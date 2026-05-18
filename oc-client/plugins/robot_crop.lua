--[[
  IC2 crop harvest helper (Phase 4).
  See kb/03-gtnh/ic2-crops.md and kb/02-opencomputers/component-robot.md

  Returns { message = "success", data = ... } for executor JSON encoding.
  No error() — use pcall around robot / component calls.
]]

_G.robot_crop = _G.robot_crop or {}
local rc = _G.robot_crop

local component = require("component")
local robot = require("robot")
local sides = require("sides")

local function yieldEvery(i)
  if i and i % 50 == 0 then
    os.sleep(0)
  end
end

local function geolyzer()
  if component.isAvailable("geolyzer") then
    return component.geolyzer
  end
  return nil
end

--- Inspect block below the robot (optional Geolyzer).
function rc.scanBelow()
  local gz = geolyzer()
  if not gz then
    return {
      message = "success",
      data = { mode = "no_geolyzer", hint = "Install Geolyzer upgrade or use Crop Manipulator peripheral" },
    }
  end
  local ok, res = pcall(function()
    return gz.analyze(sides.down)
  end)
  if not ok then
    return { message = "geolyzer failed: " .. tostring(res) }
  end
  return { message = "success", data = res or {} }
end

--- Right-click crop stick / crop below (harvest when mature — game handles rules).
function rc.harvestBelow()
  local ok, res = pcall(function()
    return robot.use(sides.down)
  end)
  if not ok then
    return { message = "robot.use failed: " .. tostring(res) }
  end
  return {
    message = "success",
    data = { used = res, side = "down" },
  }
end

--- Break block below (fallback if no right-click harvest); use with care.
function rc.swingBelow()
  local ok, res = pcall(function()
    return robot.swing(sides.down)
  end)
  if not ok then
    return { message = "robot.swing failed: " .. tostring(res) }
  end
  return { message = "success", data = { swung = res } }
end

--- Sample hardness patch under robot (Geolyzer scan(0,0) — see kb/02-opencomputers/component-geolyzer.md).
function rc.hardnessPatch()
  local gz = geolyzer()
  if not gz then
    return {
      message = "success",
      data = { note = "no geolyzer" },
    }
  end
  local ok, data = pcall(function()
    return gz.scan(0, 0)
  end)
  if not ok then
    return { message = "scan failed: " .. tostring(data) }
  end
  local n = data and #data or 0
  local preview = {}
  if data and n > 0 then
    for i = 1, math.min(16, n) do
      preview[i] = data[i]
    end
  end
  return {
    message = "success",
    data = { count = n, preview = preview },
  }
end

return rc
