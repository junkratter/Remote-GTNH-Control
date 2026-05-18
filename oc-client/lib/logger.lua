-- logger.lua
local logger = {}

-- Log levels
local levels = {
    DEBUG = 1,
    INFO  = 2,
    WARN  = 3,
    ERROR = 4
}

-- Default log level
local current_level = levels.INFO

-- Set log level by name (DEBUG, INFO, …)
function logger.set_level(level)
    local lvl = levels[level:upper()]
    if lvl then
        current_level = lvl
    else
        error("Invalid log level: " .. level)
    end
end

-- Timestamp for log lines
local function get_timestamp()
    return os.date("%Y-%m-%d %H:%M:%S")
end

-- Internal: emit one line
local function log(level_name, level_value, message)
    if level_value >= current_level then
        io.write(string.format("[%s] [%s] %s", get_timestamp(), level_name, message), '\n')
    end
end

-- Public log methods
function logger.debug(message)
    log("DEBUG", levels.DEBUG, message)
end

function logger.info(message)
    log("INFO", levels.INFO, message)
end

function logger.warn(message)
    log("WARN", levels.WARN, message)
end

function logger.error(message)
    log("ERROR", levels.ERROR, message)
end

return logger
