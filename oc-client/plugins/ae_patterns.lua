-- plugins/ae_patterns.lua — bulk ME pattern programming + AE snapshot (ADR-006).
-- Depends on globals from plugins/ae.lua (loaded first by alphabetical order).

local component = require("component")

if type(ae) ~= "table" then
    error("ae_patterns: global ae missing")
end

local function me_proxy()
    local env = require("env")
    local aeAddress = env.aeAddress
    if component.proxy(aeAddress) then
        return component.proxy(aeAddress)
    end
    if component.isAvailable("me_controller") then
        return component.me_controller
    end
    if component.isAvailable("me_interface") then
        return component.me_interface
    end
    error("AE network not found")
end

--- Run ``fn()`` only if the named crafting CPU exists and is idle.
--- Returns whatever ``fn`` returns, or a ``{ message = ... }`` table on error / busy CPU.
function ae.cpuLockedTry(cpuName, fn)
    if type(fn) ~= "function" then
        return { message = "cpuLockedTry: expected function" }
    end
    if not cpuName or cpuName == "" then
        return { message = "cpuLockedTry: cpuName is required" }
    end
    local info = ae.getCpuInfoByName(cpuName)
    if info.message ~= "success" then
        return { message = "cpuLockedTry: " .. tostring(info.message) }
    end
    if info.data and info.data.busy then
        return { message = "cpuLockedTry: CPU is busy", data = { name = cpuName } }
    end
    return fn()
end

--- Program many interface slots in one task. Each entry:
--- { interface_address=..., slot=..., kind=..., inputs={...}, outputs={...} }
--- Aliases: iface -> interface_address (matches backend oc_commands).
function ae.bulkProgramPatterns(plan)
    if type(plan) ~= "table" then
        return { message = "bulkProgramPatterns: expected table" }
    end
    local done = 0
    for i, p in ipairs(plan) do
        local addr = p.interface_address or p.iface
        if not addr or addr == "" then
            return { message = "bulkProgramPatterns: missing interface_address", data = { index = i } }
        end
        local sw = ae.setMeInterfaceAddress(addr)
        if sw.message ~= "success" then
            return sw
        end
        local slot = tonumber(p.slot) or 0
        local kind = tostring(p.kind or "processing")
        local inputs = p.inputs or {}
        local outputs = p.outputs or {}
        local pr = ae.programPattern(slot, kind, inputs, outputs)
        if pr.message ~= "success" then
            return pr
        end
        done = done + 1
        if i % 20 == 0 then
            os.sleep(0)
        end
    end
    return { message = "success", data = { programmed = done } }
end

--- Lightweight AE item list for the backend solver (no NBT bodies).
function ae.snapshotForSolver()
    local me = me_proxy()
    local items = me.getItemsInNetwork()
    if not items then
        return { message = "snapshotForSolver: no items" }
    end
    local out = {}
    local n = 0
    for _, item in pairs(items) do
        n = n + 1
        table.insert(out, {
            name = item.name,
            damage = item.damage or 0,
            size = item.size or item.amount or 0,
            label = item.label,
        })
        if n % 50 == 0 then
            os.sleep(0)
        end
    end
    return { message = "success", data = { items = out, at = os.time() } }
end
