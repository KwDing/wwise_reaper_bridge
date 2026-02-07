-- ============================================================
-- WwiseReaperBridge - Export Root Tracks
--
-- Features:
--   1. Cleans target folder completely.
--   2. Forces 48kHz / 24-bit PCM WAV.
--   3. NO BWF Chunk (Clean WAV).
--   4. Auto-detects Mono/Stereo per track.
--   5. FORCES Render Window to Close (RENDER_CLOSEPROG).
-- ============================================================

local WRB = {}
local DEFAULT_RENDER_SETTINGS = "ZXZhdxgAAQ=="

local function msg(s)
    reaper.ShowConsoleMsg(tostring(s) .. "\n")
end

local function trim(s)
    if not s then return "" end
    return (s:gsub("^%s+", ""):gsub("%s+$", ""))
end

local function read_file(path)
    local f = io.open(path, "r")
    if not f then return nil end
    local content = f:read("*all")
    f:close()
    return content
end

local function looks_like_b64(s)
    -- Very lightweight validation:
    -- - non-empty
    -- - base64 charset
    -- - length multiple of 4 is common (not guaranteed, but good sanity check)
    s = trim(s or "")
    if s == "" then return false end
    if s:find("[^%w%+%/%=]") then return false end
    return true
end

function WRB.FindConfigPath()
    local osname = reaper.GetOS():lower()
    local sep = package.config:sub(1, 1)
    local base = ""

    if osname:find("win") then
        base = os.getenv("APPDATA") or ""
        if base == "" then
            -- fallback
            local home = os.getenv("USERPROFILE") or ""
            if home ~= "" then
                base = home .. "\\AppData\\Roaming"
            end
        end
    elseif osname:find("osx") or osname:find("mac") then
        base = (os.getenv("HOME") or "") .. "/Library/Application Support"
    else
        -- Linux
        base = os.getenv("XDG_CONFIG_HOME") or ""
        if base == "" then
            base = (os.getenv("HOME") or "") .. "/.config"
        end
        if base == "/.config" or base == "" then
            -- last fallback
            base = (os.getenv("HOME") or "") .. "/.local/share"
        end
    end

    -- ensure folder exists (even if file doesn't)
    local dir = base .. sep .. "WwiseReaperBridge"
    return dir .. sep .. "config.json"
end


function WRB.GetRenderFormat()
    local config_path = WRB.FindConfigPath()
    local text = read_file(config_path)

    if not text then
        -- msg("config not found: " .. config_path)
        return DEFAULT_RENDER_SETTINGS
    end

    -- Extract: "reaper_render_format": "XXXXX"
    local fmt = text:match([["reaper_render_format"%s*:%s*"([^"]*)"]])
    fmt = trim(fmt or "")

    if looks_like_b64(fmt) then
        -- msg("found config render format: " .. fmt)
        return fmt
    end

    -- msg("config render format missing/invalid, using default: " .. DEFAULT_RENDER_SETTINGS)
    return DEFAULT_RENDER_SETTINGS
end

-- Get Render Path
function WRB.GetRenderPath()
    local osname = reaper.GetOS():lower()
    local sep = package.config:sub(1,1)
    local base_path = ""

    if osname:find("win") then
        base_path = os.getenv("LOCALAPPDATA")
        if not base_path then base_path = os.getenv("USERPROFILE") .. "\\AppData\\Local" end
    elseif osname:find("osx") or osname:find("mac") then
        base_path = os.getenv("HOME") .. "/Library/Application Support"
    else
        base_path = os.getenv("HOME") .. "/.local/share"
    end

    local full_path = base_path .. sep .. "WwiseReaperBridge" .. sep .. "renders"

    -- Ensure directory exists
    reaper.RecursiveCreateDirectory(full_path, 0)

    return full_path, sep
end

-- Cleanup Render Folder and init Flag
function WRB.CleanAndInit(dir, sep)
    local i = 0
    repeat
        local file = reaper.EnumerateFiles(dir, i)
        if file then
            os.remove(dir .. sep .. file)
            -- Note: When deleting, the index might shift, but simple enumeration usually works
            -- for bulk delete. If issues arise, we can loop backwards, but this is standard.
        end
        i = i + 1
    until not file


    -- Create Timestamp Flag (yyyy_mm_dd_hh_mm_ss.flag)
    local timestamp_name = os.date("%Y_%m_%d_%H_%M_%S") .. ".flag"
    local full_ts_path = dir .. sep .. timestamp_name

    local f = io.open(full_ts_path, "w")
    if f then
        f:write("running")
        f:close()
    end

    return full_ts_path
end

function WRB.MarkSuccess(dir, sep, old_flag_path)
    -- Remove the Timestamp flag
    if old_flag_path then
        os.remove(old_flag_path)
    end

    -- Create success.flag
    local f = io.open(dir .. sep .. "success.flag", "w")
    if f then
        f:close()
    end
end

-- Analyze Track (Time & Channels)
function WRB.AnalyzeTrackFamily(root_idx)
    local root_tr = reaper.GetTrack(0, root_idx)
    local root_depth = reaper.GetTrackDepth(root_tr)

    local max_time = 0
    local is_stereo = false

    -- Find the media ending time and channel number of items on a track
    local function CheckItems(tr)
        local cnt = reaper.CountTrackMediaItems(tr)
        for i = 0, cnt - 1 do
            local item = reaper.GetTrackMediaItem(tr, i)

            -- Check Time
            local pos = reaper.GetMediaItemInfo_Value(item, "D_POSITION")
            local len = reaper.GetMediaItemInfo_Value(item, "D_LENGTH")
            if (pos + len) > max_time then max_time = pos + len end

            -- Check Channels (Source), stereo if any source is stereo
            local take = reaper.GetActiveTake(item)
            if take then
                local src = reaper.GetMediaItemTake_Source(take)
                if src then
                    local chans = reaper.GetMediaSourceNumChannels(src)
                    if chans > 1 then is_stereo = true end
                end
            end
        end
    end

    CheckItems(root_tr)

    local total_tracks = reaper.CountTracks(0)
    for i = root_idx + 1, total_tracks - 1 do
        local child_tr = reaper.GetTrack(0, i)
        local child_depth = reaper.GetTrackDepth(child_tr)
        if child_depth <= root_depth then break end
        CheckItems(child_tr)
    end

    return max_time, is_stereo
end

function WRB.ProcessAndRender()
    local output_dir, sep = WRB.GetRenderPath()

    -- === CLEANUP & SIGNAL START ===
    local current_flag_path = WRB.CleanAndInit(output_dir, sep)

    -- === FORMAT CONFIGURATION ===
    local render_format_settings = WRB.GetRenderFormat()

    -- Set Global Render Params
    reaper.GetSetProjectInfo(0, "RENDER_SETTINGS", 3, true)   -- 3 = Selected Tracks (Stems)
    reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 2, true) -- 2 = Time Selection Bounds
    reaper.GetSetProjectInfo(0, "RENDER_SRATE", 48000, true)  -- Force 48000 Hz
    reaper.GetSetProjectInfo(0, "RENDER_DITHER", 0, true)     -- Disable Dither

    -- FORCE AUTO-CLOSE Render Window (Reaper 6/7 Feature), 1 = Close when finished
    reaper.GetSetProjectInfo(0, "RENDER_CLOSEPROG", 1, true)

    reaper.GetSetProjectInfo_String(0, "RENDER_FILE", output_dir, true)
    reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "$track", true)
    reaper.GetSetProjectInfo_String(0, "RENDER_FORMAT", render_format_settings, true)


    local track_count = reaper.CountTracks(0)
    local render_count = 0

    reaper.Main_OnCommand(40297, 0) -- Unselect all

    for i = 0, track_count - 1 do
        local tr = reaper.GetTrack(0, i)
        local parent = reaper.GetParentTrack(tr)

        -- Only process ROOT tracks
        if parent == nil then

            local end_time, is_stereo = WRB.AnalyzeTrackFamily(i)

            if end_time > 0 then
                reaper.SetTrackSelected(tr, true)
                reaper.GetSet_LoopTimeRange(true, false, 0, end_time, false)

                -- Force Mono/Stereo based on content analysis
                local channels = is_stereo and 2 or 1
                reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", channels, true)

                -- COMMAND 41824: "File: Render project, using the most recent render settings"
                -- RENDER_CLOSEPROG set to 1 above should ensure the window closes.
                reaper.Main_OnCommand(41824, 0)

                render_count = render_count + 1
                reaper.SetTrackSelected(tr, false)
            end
        end
    end

    -- SUCCESS
    WRB.MarkSuccess(output_dir, sep, current_flag_path)

    return render_count, output_dir
end

local warmup_start = nil
local WARMUP_SEC = 2.0   -- wait at least 2 seconds
local MAX_WAIT_SEC = 10.0 -- but don't wait forever

local function IsProjectReady()
    return (reaper.CountTracks(0) > 0) or (reaper.CountMediaItems(0) > 0)
end

function Main()
    -- Init warmup timer
    if not warmup_start then
        warmup_start = reaper.time_precise()
    end

    local elapsed = reaper.time_precise() - warmup_start

    -- Wait until project is actually ready AND a minimum warmup time has passed
    -- (CLI launch often runs scripts before the project/audio/media is fully ready)
    if (not IsProjectReady() or elapsed < WARMUP_SEC) and elapsed < MAX_WAIT_SEC then
        reaper.defer(Main)
        return
    end

    -- Execute Logic
    reaper.Undo_BeginBlock()
    reaper.PreventUIRefresh(1)

    WRB.ProcessAndRender()

    reaper.PreventUIRefresh(-1)
    reaper.Undo_EndBlock("WwiseReaperBridge Export", -1)
    -- reaper.Main_OnCommand(40004, 0) -- File: Quit REAPER
end

Main()