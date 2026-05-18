local internet = require("internet")
local computer = require("computer")
local os = require("os")
local filesystem = require("filesystem")
local shell = require("shell")

local env = require("env")
local logger = require("lib/logger")
local json = require("lib/json")
local dumpjson = require("lib/json2")


local executor = {}

local serverUrl = env.baseUrl .. env.getPath
local reportUrl = env.baseUrl .. env.reportPath
local chunkedReportUrl = env.baseUrl .. env.chunkedReportPath



-- Load plugins from plugins/*.lua
local function loadPlugins()
    package.path = package.path .. ";" .. shell.resolve("lib/") .. "/?.lua"
    local pluginPath = shell.resolve("plugins/")
    for file in filesystem.list(pluginPath) do
        if file:match("%.lua$") then
            local moduleName = file:sub(1, -5) -- strip ".lua"
            local success, err = pcall(function() require("plugins/" .. moduleName) end)

            if success then
                logger.info("Successfully loaded plugin: " .. moduleName)
            else
                logger.error("Error loading plugin: " .. moduleName .. err)
            end
        end
    end
end


local function getHeaders()
    local headers = {
        ["Content-Type"] = "application/json",
        ["X-Client-ID"] = env.clientId,
        ["X-Server-Token"] = env.serverToken,
    }
    return headers
end


local function close(req)
    local success = false
    if type(req.close) == "function" then
        req.close()
        success = true
    end

    if not success then
        local mt = getmetatable(req)
        if mt and mt.__index and mt.__index.close then
            mt.__index.close()
            success = true
        elseif mt and mt.__call then
            mt.__call(req, "close")
            success = true
        end
    end

    if not success then
        logger.error("Failed to close the request.")
    end
end

local function executeCommand(command_content)
    logger.debug("Executing command: " .. tostring(command_content))
    local code, loadError = load(command_content)

    if not code then
        logger.debug("Failed to load command: " .. tostring(loadError))
        return false, loadError
    end

    local success, result = xpcall(code, debug.traceback)

    if not success then
        logger.debug("Command execution failed: " .. tostring(result))
        return false, result
    end

    logger.debug("Command executed successfully")
    return true, result
end

function executor.processCommands(command_table, isChunked)
    logger.debug("Processing commands...")
    local command_result_table = {}

    for cid, command_content in pairs(command_table) do
        logger.debug("Processing command with ID: " .. tostring(cid))
        local success, command_result = executeCommand(command_content)

        if success then
            if isChunked and command_result.message == "success" then
                command_result_table[cid] = command_result.data
            else
                command_result_table[cid] = json.encode(command_result)
            end
        else
            command_result_table[cid] = json.encode({ message = command_result })
        end
    end
    return command_result_table
end

function executor.fetchCommands()
    logger.debug("Fetching commands from server...")

    local headers = getHeaders()
    local req = internet.request(serverUrl, nil, headers)
    local response = ""
    if not req then
        logger.error("Unable to connect to the server.")
        return nil, nil, nil
    end

    local startTime = computer.uptime()
    local timeout = 2 -- seconds

    while not req.finishConnect() do
        if computer.uptime() - startTime > timeout then
            logger.error("Timeout while fetching commands to the server.")
            close(req)
            return nil, nil, nil
        end
        os.sleep(0)
    end

    local chunk
    repeat
        chunk = req.read()
        if chunk then
            response = response .. chunk
        end
    until not chunk

    close(req)

    if response == "" then
        return nil, nil, nil
    end

    local res = json.decode(response)

    if not res or res.code ~= 200 then
        if res.message then
            logger.warn("Unable to fetching commands: " .. res.message)
        else
            logger.warn("Unable to fetching commands: unknown error")
        end
        return nil, nil, nil
    end

    local command_table = res.data

    if not command_table or not command_table.taskId or not command_table.commands then
        return nil, nil, nil
    end


    logger.debug("Task ID: " .. tostring(command_table.taskId))

    return command_table.taskId, command_table.commands, command_table.is_chunked
end

function executor.reportResults(taskId, command_result_table)
    logger.debug("Reporting command results to server for Task ID: " .. tostring(taskId))

    local report_data = {
        task_id = taskId,
        results = command_result_table
    }

    local headers = getHeaders()
    -- Error: too long without yielding
    -- Fix: using dumpjson instead of json.encode
    local json_data = dumpjson(report_data)
    logger.debug("Successfully encoded report data.")

    local req = internet.request(
        reportUrl,
        json_data,
        headers
    )
    os.sleep(0)
    logger.debug("Successfully to report")

    if not req then
        logger.error("Unable to connect to the server to report results.")
        return
    end

    local startTime = computer.uptime()
    local timeout = 4 -- seconds

    while not req.finishConnect() do
        if computer.uptime() - startTime > timeout then
            logger.error("Timeout while reporting results to the server.")
            close(req)
            return
        end
        os.sleep(0)
    end

    repeat
        local chunk = req.read()
    until not chunk

    logger.debug("Results for Task ID " .. tostring(taskId) .. " successfully reported.")
    close(req)
end

function executor.reportChunkedResults(taskId, command_result_table)
    logger.debug("Reporting command results to server for Task ID: " .. tostring(taskId) .. " using chunked upload.")

    local chunk_size = env.chunkSize or 128
    local total_commands = #command_result_table
    local chunked = 1 -- chunk index; 0 means final chunk for API

    for i = 1, total_commands, chunk_size do
        local chunked_result = {}

        for j = i, math.min(i + chunk_size - 1, total_commands) do
            chunked_result[#chunked_result + 1] = command_result_table[j]
        end
        chunked = i
        if i + chunk_size - 1 >= total_commands then
            chunked = 0 -- API: 0 marks last chunk
        end

        local report_data = {
            task_id = taskId,
            results = chunked_result
        }

        local headers = getHeaders()

        local req = internet.request(
            chunkedReportUrl .. "?chunked=" .. tostring(chunked),
            json.encode(report_data),
            headers
        )

        if not req then
            logger.error("Unable to connect to the server to report chunked results.")
            return
        end

        local startTime = computer.uptime()
        local timeout = 4 -- seconds

        while not req.finishConnect() do
            if computer.uptime() - startTime > timeout then
                logger.error("Timeout while reporting chunked results to the server.")
                close(req)
                return
            end
            os.sleep(0)
        end

        repeat
            local chunk = req.read()
        until not chunk

        logger.debug("Chunked results for Task ID " .. tostring(taskId) .. " successfully reported: " .. tostring(chunked))
        close(req)

        if chunked == 0 then
            break
        end
        os.sleep(0.2)
    end
    logger.debug("Report done.")
end

loadPlugins()

return executor
