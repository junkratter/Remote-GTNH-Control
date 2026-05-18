local component = require("component")
local base64 = require("lib.base64")
local env = require("env")

local aeAddress = env.aeAddress

local me

if component.proxy(aeAddress) then
    me = component.proxy(aeAddress)
elseif component.isAvailable("me_controller") then
    me = component.me_controller
elseif component.isAvailable("me_interface") then
    me = component.me_interface
else
    error("AE network not found")
end

ae = {}


local function parseItem(items)
    if items == nil then return nil end
    local data = {}
    for i, item in pairs(items) do
        if item.hasTag and item.tag ~= nil then
            item.tag = base64.encode(item.tag)
        end
        table.insert(data, item)
        
        -- Yield periodically to avoid "too long without yielding"
        if i % 50 == 0 then
            os.sleep(0)
        end
    end
    return data
end

local function getSimpleInfo(cpu)
    return {
        cpu = {},
        busy = cpu.busy,
        coprocessors = cpu.coprocessors,
        storage = cpu.storage,
        name = cpu.name
    }
end

local function simpleItemInfo(item)
    if item == nil then return nil end
    return {
        name = item.name,
        label = item.label,
        damage = item.damage,
        size = item.size,
        isCraftable = item.isCraftable
    }
end

local function simpleItemsInfo(items)
    if items == nil then return end
    for i, item in pairs(items) do
        items[i] = simpleItemInfo(item)
        if i % 50 == 0 then
            os.sleep(0)
        end
    end
end

local function removeEmptyItem(items)
    if items == nil then return nil end

    local newOne = {}
    for i, item in pairs(items) do
        if item.size ~= nil and item.size ~= 0 or item.amount ~= nil and item.amount ~= 0 then
            table.insert(newOne, simpleItemInfo(item))
        end
        if i % 50 == 0 then
            os.sleep(0)
        end
    end
    return newOne
end

local function getDetailInfo(cpu)
    local sub = cpu.cpu
    local result = {
        activeItems = removeEmptyItem(sub.activeItems()),
        -- Base64-encode tag when present (avoids encoding issues)
        finalOutput = simpleItemInfo(sub.finalOutput()),
        active = sub.isActive(),
        busy = sub.isBusy(),
        pendingItems = removeEmptyItem(sub.pendingItems()),
        storedItems = removeEmptyItem(sub.storedItems())
    }
    return result
end

function ae.getCpuInfoByName(cpuName)
    if not cpuName or cpuName == "" then
        return { message = "CPU name is empty" }
    end

    local cpus = me.getCpus()
    if not cpus then
        return { message = "No CPUs found" }
    end

    for _, cpu in pairs(cpus) do
        if cpu.name == cpuName then
            return { message = "success", data = getSimpleInfo(cpu) }
        end
    end

    return { message = "No CPU named " .. cpuName }
end

function ae.getCpuList(detail)
    -- List all CPUs (optionally with per-CPU detail)
    local cpus = me.getCpus()
    if cpus == nil then return { message = "no cpus" } end
    local result = {}
    for _, cpu in pairs(cpus) do
        local simple = getSimpleInfo(cpu)
        if detail then simple.cpu = getDetailInfo(cpu) end
        table.insert(result, simple)
    end
    return { message = "success", data = result}
end

function ae.getCpuDetail(cpuName)
    -- CPU detail by name
    local cpus = me.getCpus()
    if cpus == nil then return nil end
    for _, cpu in pairs(cpus) do
        if cpu.name == cpuName then
            local result = getSimpleInfo(cpu)
            result.cpu = getDetailInfo(cpu)
            return result
        end
    end
    return { message = "no cpus" }
end

function ae.requestItem(name, damage, amount, cpuName, label)
    -- Request crafting for an item.
    -- Args:
    -- name (string): item registry name
    -- damage (int): meta / damage value
    -- amount (int, optional): how many to craft, default 1
    -- cpuName (string, optional): crafting CPU; if empty the system picks one
    -- label (string, optional): item label (e.g. fluid drops)
    if not name or not damage then
        return { message = "Item name or damage is missing" }
    end

    local craftable
    if label then
        craftable = me.getCraftables({
            name = name,
            damage = damage,
            label = label
        })[1]
    else
        craftable = me.getCraftables({
            name = name,
            damage = damage
        })[1]
    end

    if not craftable then
        return { message = "Item is not craftable" }
    end

    amount = amount or 1


    local result
    if not cpuName or cpuName == "" then
        result = craftable.request(amount, true)
    else
        -- Ensure CPU exists and is idle when a CPU name is given
        local cpuInfo = ae.getCpuInfoByName(cpuName)
        if cpuInfo.message == "success" then
            if cpuInfo.data.busy then
                return { message = "CPU is busy" }
            else
                result = craftable.request(amount, nil, cpuName)
            end
        else
            return { message = "CPU not found", data = cpuInfo }
        end
    end

    if not result then
        return { message = "Craft request failed" }
    end

    local res = {
        item = craftable.getItemStack(),
        failed = result.hasFailed() or false,
        computing = result.isComputing() or false,
        done = { result = false, why = nil },
        canceled = { result = false, why = nil }
    }

    res.done.result, res.done.why = result.isDone()
    res.canceled.result, res.canceled.why = result.isCanceled()

    return { message = "success", data = res }
end

function ae.getAllSilempleItems(filter)
    -- All items in network (simple fields only)
    local items = me.getItemsInNetwork(filter)
    local newOne = {}
    for i, item in pairs(items) do
        if item.size ~= nil or item.amount ~= nil then
            table.insert(newOne, simpleItemInfo(item))
        end
        if i % 50 == 0 then
            os.sleep(0)
        end
    end
    return { message = "success", data = newOne}
end

function ae.getAllItems(filter)
    -- All items in network (full payload, tags base64)
    local items = me.getItemsInNetwork(filter)
    return { message = "success", data = parseItem(items) }
end

function ae.getAllFluids()
    -- All fluids in network
    local fluids = me.getFluidsInNetwork()
    return { message = "success", data = parseItem(fluids) }
end

function ae.getAllEssentia()
    -- All essentia in network
    local essentia = me.getEssentiaInNetwork()
    return { message = "success", data = parseItem(essentia) }
end

function ae.getAllCraftables()
    -- Craftable items derived from network scan
    local items = me.getItemsInNetwork()
    if not items then return { message = "not items" } end

    local result = {}
    for _, item in pairs(items) do
    if item.isCraftable then
        local entry = {
            name = item.name,
            label = item.label,
            size = item.size,
            damage = item.damage
        }
        
        if item.hasTag and item.tag ~= nil then
            entry.hasTag = true
            entry.tag = base64.encode(item.tag)
        end
        
        table.insert(result, entry)
        end
    end

    return { message = "success", data = result }
end

-- ============================================================================
-- ME Interface programming (Phase 3 — Autocraft patterns)
-- ============================================================================
-- The pattern programming API is exposed by GregTech ME Interfaces in GTNH.
-- We treat each interface as a separate component proxy: callers switch it
-- with `ae.setMeInterfaceAddress(addr)` and then call `iface.*` methods.

iface = nil

function ae.setMeInterfaceAddress(addr)
    if not addr or addr == "" then
        return { message = "iface address is empty" }
    end
    local proxy = component.proxy(addr)
    if not proxy then
        return { message = "ME interface not found: " .. addr }
    end
    iface = proxy
    return { message = "success", data = { address = addr } }
end

local function buildPatternStack(item)
    return {
        name = item.name,
        damage = item.damage or 0,
        size = item.amount or item.size or 1,
        label = item.label,
    }
end

function ae.programPattern(slot, kind, inputs, outputs)
    -- One-shot helper: clear the slot and re-apply inputs/outputs in one task.
    if iface == nil then
        return { message = "ME interface not selected" }
    end
    local removeFn = iface.removeInterfacePattern or iface.clearPattern
    if removeFn then pcall(removeFn, iface, slot) end

    local inFn = iface.setInterfacePatternInput
    local outFn = iface.setInterfacePatternOutput
    if not inFn or not outFn then
        return { message = "ME interface lacks setInterfacePattern* API" }
    end

    for i, item in ipairs(inputs or {}) do
        local ok, err = pcall(inFn, iface, slot, buildPatternStack(item), i)
        if not ok then
            return { message = "setInput failed: " .. tostring(err) }
        end
    end
    for i, item in ipairs(outputs or {}) do
        local ok, err = pcall(outFn, iface, slot, buildPatternStack(item), i)
        if not ok then
            return { message = "setOutput failed: " .. tostring(err) }
        end
    end
    return { message = "success", data = { slot = slot, kind = kind } }
end

function ae.cancelCraftingByCpuName(cpuName)
    -- Cancel active crafting on a CPU by name.
    -- cpuName (string): target CPU; no-op if empty.

    if not cpuName or cpuName == "" then
        return { message = "CPU name is empty; nothing to cancel" }
    end

    local cpus = me.getCpus()
    if not cpus then
        return { message = "No CPUs in network" }
    end

    for _, cpu in pairs(cpus) do
        if cpu.name == cpuName then
            local currentCpu = cpu.cpu
            if currentCpu then
                currentCpu.cancel()
                return { message = "Cancelled crafting on CPU: " .. cpuName }
            else
                return { message = "Failed to cancel crafting on CPU: " .. cpuName }
            end
        end
    end

    return { message = "No CPU named " .. cpuName }
end
