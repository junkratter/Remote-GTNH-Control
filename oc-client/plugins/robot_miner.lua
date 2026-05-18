--[[
  GT miner deployment helper (Phase 4 skeleton).
  Full navigation + placement is environment-specific (GPS, waypoints).
  See kb/03-gtnh/gt-miner.md — state machine is authoritative on the backend.

  Lua side: format telemetry / acknowledge phases from polled tasks.
]]

_G.robot_miner = _G.robot_miner or {}
local rm = _G.robot_miner

local robot = require("robot")
local sides = require("sides")

--- Health check from a task command: `return robot_miner.ping()`
function rm.ping()
  local okE, energy = pcall(function()
    return require("computer").energy()
  end)
  local okS, sel = pcall(function()
    return robot.select(1)
  end)
  return {
    message = "success",
    data = {
      energy_ok = okE,
      energy = okE and energy or nil,
      select_ok = okS,
      select = okS and sel or nil,
    },
  }
end

--- Record intent for a mining job (coordinates from server UI). Does not move yet.
-- opts: { job_id = n, x=, y=, z=, dim=0, miner_kind="advanced_miner" }
function rm.acceptJob(opts)
  opts = opts or {}
  return {
    message = "success",
    data = {
      phase = "accepted",
      job_id = opts.job_id,
      target = { x = opts.x, y = opts.y, z = opts.z, dim = opts.dim or 0 },
      miner_kind = opts.miner_kind or "advanced_miner",
      note = "Navigation/placement not automated in this build — drive robot or add GPS script.",
    },
  }
end

--- Placeholder: robot tries forward place (slot must hold miner block).
function rm.placeForward()
  local ok, res = pcall(function()
    return robot.place(sides.front)
  end)
  if not ok then
    return { message = "place failed: " .. tostring(res) }
  end
  return { message = "success", data = { placed = res, side = "front" } }
end

--- acceptJob + placeForward (robot must be at target, slot 1 = miner block).
function rm.deploy(opts)
  opts = opts or {}
  local accepted = rm.acceptJob(opts)
  if accepted.message ~= "success" then
    return accepted
  end
  if opts.miner_slot then
    robot.select(opts.miner_slot)
  end
  return rm.placeForward()
end

return rm
