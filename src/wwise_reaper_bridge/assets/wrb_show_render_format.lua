-- ============================================================
-- Show Active Project Render Format String (RENDER_FORMAT)
-- ============================================================

reaper.ClearConsole()

local proj = 0 -- active project

-- Get the render format string (Base64-like blob)
local ok, fmt = reaper.GetSetProjectInfo_String(
    proj,
    "RENDER_FORMAT",
    "",
    false
)

if ok and fmt ~= "" then
    reaper.ShowConsoleMsg("=== Render Format String (RENDER_FORMAT) ===\n")
    reaper.ShowConsoleMsg(fmt .. "\n")
    reaper.ShowConsoleMsg("=== copy the line above ===")
else
    reaper.ShowConsoleMsg("Could not read RENDER_FORMAT\n")
end
