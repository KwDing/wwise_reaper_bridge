-- ============================================================
-- WwiseReaperBridge - Import Tracks from last_selected.txt
--
-- Reads:
--   Windows: %LOCALAPPDATA%\WwiseReaperBridge\last_selected.txt
--   macOS:   ~/Library/Application Support/WwiseReaperBridge/last_selected.txt
--   Linux:   ~/.local/share/WwiseReaperBridge/last_selected.txt
--
-- Each non-empty line:
--   wwise_path|sourcepath(optional)
--
-- For each line:
--   - Track name = last component of wwise_path (supports \ or /)
--   - Track notes (P_NOTES) = full wwise_path
--   - If sourcepath exists, insert media at time 0 on this track
-- ============================================================

local WRB = {}

function WRB.Trim(s)
    if s == nil then
        return ""
    end
    return s:match("^%s*(.-)%s*$")
end

function WRB.SplitManifestLine(line)
    -- Format: left|right(optional)
    local left, right = line:match("^(.-)%|(.*)$")
    if not left then
        return WRB.Trim(line), ""
    end
    return WRB.Trim(left), WRB.Trim(right)
end

function WRB.GetLastPathComponent(p)
    if not p or p == "" then
        return "WwiseItem"
    end
    -- Accept both \ and /
    local name = p:match("([^\\/]+)$")
    if not name or name == "" then
        return "WwiseItem"
    end
    return name
end

-- function WRB.SanitizeTrackName(name)
--     name = WRB.Trim(name or "")
--     if name == "" then
--         name = "WwiseItem"
--     end
--     -- Remove characters illegal on Windows/macOS
--     name = name:gsub('[\\/:*?"<>|]', "_")
--     -- Avoid trailing dots/spaces on Windows
--     name = name:gsub("[%.%s]+$", "")
--     if name == "" then
--         name = "WwiseItem"
--     end
--     return name
-- end

function WRB.FileExists(path)
    if not path or path == "" then
        return false
    end
    local f = io.open(path, "rb")
    if f then
        f:close()
        return true
    end
    return false
end

function WRB.GetManifestPath()
    local osname = reaper.GetOS():lower()

    -- Prefer LOCALAPPDATA on Windows
    local localapp = os.getenv("LOCALAPPDATA")
    if localapp and localapp ~= "" then
        return localapp .. "\\WwiseReaperBridge\\last_selected.txt"
    end

    -- macOS
    if osname:find("osx") or osname:find("mac") then
        local home = os.getenv("HOME") or ""
        if home ~= "" then
            return home .. "/Library/Application Support/WwiseReaperBridge/last_selected.txt"
        end
    end

    -- Linux / fallback
    local home = os.getenv("HOME") or ""
    if home ~= "" then
        return home .. "/.local/share/WwiseReaperBridge/last_selected.txt"
    end

    -- Last resort: REAPER resource path
    return reaper.GetResourcePath() .. "/WwiseReaperBridge/last_selected.txt"
end

function WRB.UnselectAllTracks()
    reaper.Main_OnCommand(40297, 0) -- Track: Unselect all tracks
end

function WRB.CreateTrackAtEnd()
    local idx = reaper.CountTracks(0)
    reaper.InsertTrackAtIndex(idx, true)
    return reaper.GetTrack(0, idx)
end

function WRB.SetTrackNameAndNotes(tr, name, notes)
    reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", name, true)
    reaper.GetSetMediaTrackInfo_String(tr, "P_NOTES", notes, true)
end

-- function WRB.InsertMediaOnSpecificTrack(tr, source_path)
--     -- Ensure InsertMedia goes to the correct track:
--     -- select only this track and insert at edit cursor (we set cursor=0 once)
--     WRB.UnselectAllTracks()
--     reaper.SetTrackSelected(tr, true)
--     reaper.InsertMedia(source_path, 0)
--     reaper.SetTrackSelected(tr, false)
-- end

function WRB.InsertMediaOnSpecificTrack(tr, source_path)
    -- Hard guarantee: create item + take on this track, attach file source
    local item = reaper.AddMediaItemToTrack(tr)
    if not item then
        return false
    end

    reaper.SetMediaItemInfo_Value(item, "D_POSITION", 0.0)

    local take = reaper.AddTakeToMediaItem(item)
    if not take then
        reaper.DeleteTrackMediaItem(tr, item)
        return false
    end

    local src = reaper.PCM_Source_CreateFromFile(source_path)
    if not src then
        reaper.DeleteTrackMediaItem(tr, item)
        return false
    end

    reaper.SetMediaItemTake_Source(take, src)

    -- Set item length to source length if known
    local src_len = reaper.GetMediaSourceLength(src)
    if src_len and src_len > 0 then
        reaper.SetMediaItemInfo_Value(item, "D_LENGTH", src_len)
    end

    return true
end


function WRB.ReadManifestLines(manifest_path)
    local f = io.open(manifest_path, "r")
    if not f then
        return nil, "Manifest TXT not found: " .. tostring(manifest_path)
    end

    local entries = {}
    for line in f:lines() do
        line = WRB.Trim(line)
        if line ~= "" then
            local wwise_path, source_path = WRB.SplitManifestLine(line)
            wwise_path = WRB.Trim(wwise_path)
            source_path = WRB.Trim(source_path)

            if wwise_path ~= "" then
                table.insert(entries, {
                    wwise_path = wwise_path,
                    source_path = source_path,
                })
            end
        end
    end

    f:close()
    return entries, nil
end

function WRB.ImportOneEntry(entry)
    local wwise_path = entry.wwise_path
    local source_path = entry.source_path

    local objname = WRB.GetLastPathComponent(wwise_path)

    local tr = WRB.CreateTrackAtEnd()
    WRB.SetTrackNameAndNotes(tr, objname, wwise_path)

    local inserted = 0
    if source_path ~= "" and WRB.FileExists(source_path) then
        local insertSuccess = WRB.InsertMediaOnSpecificTrack(tr, source_path)
        inserted = (insertSuccess and 1 or 0)
    end

    return 1, inserted
end

local function Main()
    local manifest_path = WRB.GetManifestPath()

    local entries, err = WRB.ReadManifestLines(manifest_path)
    if not entries then
        return {
            ok = false,
            manifest_path = manifest_path,
            created = 0,
            inserted = 0,
            err = err,
        }
    end

    -- Keep state clean so inserts don't go to the wrong track
    WRB.UnselectAllTracks()

    local created = 0
    local inserted = 0

    for _, entry in ipairs(entries) do
        local c, i = WRB.ImportOneEntry(entry)
        created = created + c
        inserted = inserted + i
    end

    return {
        ok = true,
        manifest_path = manifest_path,
        created = created,
        inserted = inserted,
        err = nil,
    }
end

local function Run()
    local track_count = reaper.CountTracks(0)
    local item_count = reaper.CountMediaItems(0)

    if track_count > 0 or item_count > 0 then
    -- If the project is not empty, create a New Project Tab.
    -- Command ID 40859 = "File: New project tab"
        reaper.Main_OnCommand(40859, 0)
    end

    reaper.Undo_BeginBlock()
    reaper.PreventUIRefresh(1)
    reaper.SetEditCurPos(0, false, false)

    local ok, result_or_err = pcall(Main)

    reaper.TrackList_AdjustWindows(false)
    reaper.UpdateArrange()

    reaper.PreventUIRefresh(-1)
    reaper.Undo_EndBlock("WwiseReaperBridge Import Tracks from Wwise", -1)

    if not ok then
        reaper.ShowMessageBox(
            "Script error:\n\n" .. tostring(result_or_err),
            "WwiseReaperBridge Error",
            0
        )
        return
    end

    local res = result_or_err
    if not res.ok then
        reaper.ShowMessageBox(
            tostring(res.err) .. "\n\nPath:\n" .. tostring(res.manifest_path),
            "WwiseReaperBridge Error",
            0
        )
        return
    end

--     reaper.ShowMessageBox(
--         "Imported tracks: " .. tostring(res.created) ..
--         "\nInserted media: " .. tostring(res.inserted) ..
--         "\n\nManifest:\n" .. tostring(res.manifest_path),
--         "WwiseReaperBridge",
--         0
--     )
end

Run()