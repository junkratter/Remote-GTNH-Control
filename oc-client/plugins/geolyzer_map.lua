--[[
  Phase 5 — push geolyzer / world observations to backend /api/map/scan.
  See kb/02-opencomputers/component-geolyzer.md and kb/01-architecture/decisions/004-map-phase5.md

  Usage from a polled task:
    return geolyzer_map.push({ { dimension=0, x=1, y=64, z=2, block_name="minecraft:stone", hardness=1.5 } })
  Or build one cell from analyze(side) with coords you already know:
    return geolyzer_map.analyzeAt(0, x, y, z, sides.front)
]]

_G.geolyzer_map = _G.geolyzer_map or {}
local gm = _G.geolyzer_map

local internet = require("internet")
local computer = require("computer")
local json = require("lib/json")
local env = require("env")
local component = require("component")
local sides = require("sides")

local function req_close(req)
  if req and type(req.close) == "function" then
    pcall(function()
      req.close()
    end)
  end
end

local function post_json(path, payload)
  local url = env.baseUrl .. path
  local body = json.encode(payload)
  local headers = {
    ["Content-Type"] = "application/json",
    ["X-Server-Token"] = env.serverToken,
    ["X-Client-ID"] = env.clientId,
  }
  local req = internet.request(url, body, headers)
  if not req then
    return false, "no connection"
  end
  local start = computer.uptime()
  while not req.finishConnect() do
    if computer.uptime() - start > 12 then
      req_close(req)
      return false, "connect timeout"
    end
    os.sleep(0)
  end
  local parts = {}
  repeat
    local chunk = req.read()
    if chunk then
      parts[#parts + 1] = chunk
    end
    os.sleep(0)
  until not chunk
  req_close(req)
  local text = table.concat(parts)
  local ok, parsed = pcall(json.decode, text)
  if not ok or type(parsed) ~= "table" then
    return false, text
  end
  return parsed.code == 200, parsed
end

--- POST batch of BlockObservation rows (same shape as /api/map/scan).
function gm.push(observations)
  observations = observations or {}
  local path = env.mapScanPath or "/api/map/scan"
  local ok, res = post_json(path, { observations = observations })
  if not ok then
    return { message = "map push failed: " .. tostring(res) }
  end
  return { message = "success", data = (res and res.data) or {} }
end

--- Single cell from geolyzer.analyze(side); caller supplies world coords.
function gm.analyzeAt(dimension, x, y, z, side)
  side = side or sides.front
  local geo = component.geolyzer
  if not geo then
    return { message = "no geolyzer" }
  end
  local ok, info = pcall(function()
    return geo.analyze(side)
  end)
  if not ok then
    return { message = "analyze failed: " .. tostring(info) }
  end
  return {
    message = "success",
    data = {
      dimension = dimension or 0,
      x = x,
      y = y,
      z = z,
      block_name = info and info.name or nil,
      hardness = info and info.hardness or nil,
      fluid = nil,
      meta = (type(info) == "table") and info or {},
    },
  }
end

return gm
