--[[
  GT power deploy helper — combustion generator / gas turbine + fuel capsules.
  Same MVP as robot_miner: coordinates from backend, manual navigation.

  generator_kind examples:
    combustion_generator, advanced_combustion_generator, gas_turbine
  fuel_kind examples:
    diesel, gasoline, gas, ethanol, creosote
]]

_G.robot_power = _G.robot_power or {}
local rp = _G.robot_power

local robot = require("robot")
local sides = require("sides")

function rp.ping()
  local okE, energy = pcall(function()
    return require("computer").energy()
  end)
  return {
    message = "success",
    data = {
      energy_ok = okE,
      energy = okE and energy or nil,
    },
  }
end

--- opts: { job_id, x, y, z, dim, generator_kind, fuel_kind, capsule_count, fuel_slots }
function rp.acceptJob(opts)
  opts = opts or {}
  return {
    message = "success",
    data = {
      phase = "accepted",
      job_id = opts.job_id,
      target = { x = opts.x, y = opts.y, z = opts.z, dim = opts.dim or 0 },
      generator_kind = opts.generator_kind or "advanced_combustion_generator",
      fuel_kind = opts.fuel_kind or "diesel",
      capsule_count = opts.capsule_count or 4,
      note = "Navigation not automated — drive robot to target, then placeForward + insertFuel.",
    },
  }
end

function rp.placeForward()
  local ok, res = pcall(function()
    return robot.place(sides.front)
  end)
  if not ok then
    return { message = "place failed: " .. tostring(res) }
  end
  return { message = "success", data = { placed = res, side = "front" } }
end

--- Insert fuel from inventory slots into machine in front (right-click).
-- opts: { fuel_slots = {2,3,4}, side = sides.front, max_per_slot = 1 }
function rp.insertFuel(opts)
  opts = opts or {}
  local fuel_slots = opts.fuel_slots or { 2, 3, 4, 5, 6 }
  local side = opts.side or sides.front
  local max_per_slot = opts.max_per_slot or 1
  local results = {}
  local n = 0

  for _, slot in ipairs(fuel_slots) do
    robot.select(slot)
    if robot.count() < 1 then
      results[#results + 1] = { slot = slot, skipped = true, reason = "empty" }
    else
      for _ = 1, max_per_slot do
        if robot.count() < 1 then
          break
        end
        local ok, res = pcall(function()
          return robot.use(side)
        end)
        results[#results + 1] = { slot = slot, ok = ok, res = res }
        n = n + 1
        if n % 50 == 0 then
          os.sleep(0)
        end
      end
    end
    os.sleep(0)
  end

  return { message = "success", data = { results = results } }
end

--- Alias for GT fuel capsules (diesel/gas cells in robot inventory).
function rp.insertCapsules(opts)
  opts = opts or {}
  opts.max_per_slot = opts.max_per_slot or (opts.capsule_count or 1)
  return rp.insertFuel(opts)
end

--- Full deploy: accept metadata, place generator, load fuel slots.
-- opts: same as acceptJob + generator_slot, fuel_slots
function rp.deploy(opts)
  opts = opts or {}
  local accepted = rp.acceptJob(opts)
  if accepted.message ~= "success" then
    return accepted
  end

  if opts.generator_slot then
    robot.select(opts.generator_slot)
  end

  local placed = rp.placeForward()
  if placed.message ~= "success" then
    return placed
  end

  local fueled = rp.insertCapsules({
    fuel_slots = opts.fuel_slots,
    capsule_count = opts.capsule_count,
    max_per_slot = opts.max_per_slot,
  })

  return {
    message = "success",
    data = {
      accepted = accepted.data,
      placed = placed.data,
      fueled = fueled.data,
    },
  }
end

return rp
