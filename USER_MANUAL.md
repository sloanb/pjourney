# pjourney — User Manual

**Your personal photography journal, from loading to development.**

---

## What is pjourney?

pjourney is a terminal-based application that helps photographers manage their gear and track film rolls from the moment you load the camera to the day your negatives come back from the lab. It works equally well whether you shoot film or digital.

Think of it as a logbook for your photography — recording which camera and lens you used, what film you shot, your technical settings for each frame, and a history of your equipment maintenance.

---

## Getting Started

### Launch the App

```
python main.py
```

### Logging In

When pjourney starts you will see a brief splash screen, then the login form.

- **Default username:** `admin`
- **Default password:** `pjourney`

You can also create a new account from the login screen. All of your data is stored locally on your computer at `~/.pjourney/pjourney.db`.

---

## The Dashboard — Your Home Base

After logging in you land on the Dashboard. This is the central hub for everything in pjourney.

At a glance the Dashboard shows you:

- **Inventory counts** — how many cameras, lenses, film stocks, and rolls you have recorded
- **Most-used gear** — the camera, lens, and film stock you have reached for most often
- **Currently loaded cameras** — any cameras with film actively loaded or being shot

### Navigating from the Dashboard

| Key | Destination |
|-----|-------------|
| `c` | Cameras |
| `l` | Lenses |
| `f` | Film Stock |
| `r` | Rolls |
| `a` | Admin |
| `q` | Quit |

---

## Part 1 — Setting Up Your Gear

Before you can start logging rolls, you need to add your equipment. Do this once and update as your collection changes.

---

### Cameras

Press `c` from the Dashboard to open your camera list.

**Adding a camera**

Press `a` to open the Add Camera form. Fill in as much or as little as you know:

| Field | Notes |
|-------|-------|
| Name | A nickname you will recognise (e.g. "My M6", "Black F3") |
| Make | Manufacturer (e.g. Leica, Nikon, Canon) |
| Model | Model name (e.g. M6, F3, AE-1) |
| Serial Number | Useful for insurance or service records |
| Year Built | Year the camera was manufactured |
| Year Purchased | Year you acquired it |
| Purchased From | Shop, auction, friend, etc. |
| Camera Type | **Film** or **Digital** |
| Sensor Size | For digital cameras: Full Frame, APS-C, Micro Four Thirds, etc. |
| Description | Free-form notes about this body |
| Notes | Additional notes (maintenance history, quirks, etc.) |

Press **Save** or hit `Enter` when the form is complete.

**Camera actions**

| Key | Action |
|-----|--------|
| `a` | Add a new camera |
| `e` | Edit the selected camera |
| `Enter` | Open Camera Detail (issues and maintenance log) |
| `d` | Delete the selected camera |
| `Esc` | Return to Dashboard |

---

### Camera Issues & Maintenance Log

Every camera has its own detail page where you can track known problems or maintenance history. Select a camera and press `Enter` to open it.

This is useful for recording:
- Light seals that need replacing
- Shutter speeds that are running slow
- A repair that was done and when
- Anything that affects how you use the camera

**Issue fields:**

| Field | Notes |
|-------|-------|
| Description | What the problem is |
| Date Noted | When you first noticed it (YYYY-MM-DD) |
| Notes | Any additional detail |
| Resolved | Whether the issue has been fixed |

When you get a repair done, select the issue and press `r` to mark it resolved. pjourney records the date it was resolved automatically.

| Key | Action |
|-----|--------|
| `a` | Log a new issue |
| `r` | Mark the selected issue as resolved |
| `Esc` | Back to Cameras |

To delete an issue, use the **Delete Issue** button at the bottom of the screen.

---

### Lenses

Press `l` from the Dashboard to open your lens list.

**Adding a lens**

Press `a` to open the Add Lens form:

| Field | Notes |
|-------|-------|
| Name | A nickname (e.g. "Cron 35", "Nifty Fifty") |
| Make | Manufacturer |
| Model | Model name |
| Focal Length | e.g. 35mm, 50mm, 90mm |
| Max Aperture | e.g. 1.4, 2, 2.8 |
| Filter Diameter | In millimetres (e.g. 46, 52, 58) |
| Year Built | Year manufactured |
| Year Purchased | Year you acquired it |
| Purchase Location | Where you bought it |

**Lens actions**

| Key | Action |
|-----|--------|
| `a` | Add a new lens |
| `e` | Edit the selected lens |
| `Enter` | Open Lens Detail (notes) |
| `d` | Delete the selected lens |
| `Esc` | Return to Dashboard |

---

### Lens Notes

Each lens has a notes page for anything you want to remember about it — focus shift at wide apertures, calibration history, cleaning records, or which adapters it needs. Select a lens and press `Enter`.

Notes are timestamped automatically and can be edited later.

| Key | Action |
|-----|--------|
| `a` | Add a new note |
| `e` | Edit the selected note |
| `d` | Delete a note |
| `Esc` | Back to Lenses |

---

### Film Stock

Press `f` from the Dashboard to open your film stock catalogue.

A film stock entry represents a type of film you own or have used — not a specific roll. Think of it as a recipe card: you define the film once, then use that definition when creating rolls.

**Adding a film stock**

| Field | Notes |
|-------|-------|
| Brand | Manufacturer (e.g. Kodak, Ilford, Fujifilm) |
| Name | Film name (e.g. Portra 400, HP5 Plus, Provia 100F) |
| Type | **Color** or **Black & White** |
| ISO | Box speed (e.g. 100, 400, 3200) |
| Format | 35mm, 120, 4x5, or 8x10 |
| Frames Per Roll | Typically 36 for 35mm, 12 for 120 |
| Quantity On Hand | How many rolls of this stock you currently have |
| Notes | Anything useful — development times, push/pull notes |

**Film stock actions**

| Key | Action |
|-----|--------|
| `a` | Add a new film stock |
| `e` | Edit the selected stock |
| `d` | Delete the selected stock |
| `Esc` | Return to Dashboard |

---

## Part 2 — Shooting a Roll of Film

Once your gear is set up, here is the full workflow for tracking a roll of film from the box to the darkroom.

---

### Step 1 — Create a New Roll

Press `r` from the Dashboard to open the Rolls screen, then press `n` (New Roll).

Select the film stock from the dropdown and add any notes (batch number, where you bought it, etc.). Press **Create**.

pjourney automatically creates frame entries based on the number of frames defined in your film stock. A fresh roll starts with the status **Fresh**.

---

### Step 2 — Load the Camera

Select your fresh roll and press `l` (Load).

Choose your camera from the dropdown. Optionally choose a default lens — this will pre-populate all of your frame records with that lens, saving you time when logging shots later.

After loading, the roll status advances to **Loaded** and the load date is recorded.

---

### Step 3 — Start Shooting

When you start making exposures, select the roll and press `s` (advance Status). The status moves to **Shooting**.

---

### Step 4 — Log Your Frames

Select the roll and press `f` to open the Frames screen. You will see one row per frame in the roll.

Select a frame and press `e` to edit it:

| Field | Notes |
|-------|-------|
| Subject | What you photographed |
| Aperture | e.g. f/2.8, f/8 |
| Shutter Speed | e.g. 1/125, 1/30 |
| Lens | Defaults to the roll lens; can override per frame |
| Date Taken | YYYY-MM-DD |
| Location | Where you were shooting |
| Notes | Anything else worth remembering |

You can fill this in as you shoot or at the end of the day — whatever fits your workflow.

---

### Step 5 — Finish the Roll

When you have exposed all the frames and rewound the film, select the roll and press `s` to advance the status to **Finished**. The finish date is recorded.

---

### Step 6 — Send for Development

When you are ready to develop the roll, press `s`. pjourney asks how the roll will be developed:

- **Self Develop** — opens a form to record the process type (B&W, C-41, E-6, etc.) and each development step (chemical, temperature, time, agitation). After pressing **Save**, the roll advances directly to **Developed** in one step — the Developing stage is skipped because you process the roll yourself and the result is immediate.
- **Send to Lab** — opens a form to record the lab name, contact details, and cost. After pressing **Save**, the status advances to **Developing** and the sent-for-development date is recorded.
- **Cancel** — returns to the Rolls screen without advancing the status.

To review development details later, select the roll and press `i` (Dev Info).

---

### Step 7 — Mark as Developed (Lab Only)

If you sent the roll to a lab, press `s` one final time when your negatives come back to mark the roll as **Developed**. The developed date is recorded.

If you self-developed, the roll is already **Developed** after Step 6 — this step does not apply.

You now have a complete record of the roll: when it was loaded, finished, sent, and developed — with per-frame technical notes attached.

---

### Roll Status Overview

```
Fresh → Loaded → Shooting → Finished → Developing → Developed
                                    ↘ (Self Develop) → Developed
```

Lab develop follows the full path through Developing. Self develop skips Developing and advances directly to Developed. Each transition records a date automatically. Use the filter buttons at the top of the Rolls screen to see only rolls at a particular stage.

---

## Part 3 — Digital Photography

pjourney works for digital shooters too. When adding a camera, set the type to **Digital** and select the appropriate sensor size. Rolls can still be used to represent a shooting session, memory card, or project — just set the frames per roll to whatever number makes sense for your workflow.

---

## Part 4 — Admin & Maintenance

Press `a` from the Dashboard to open the Admin screen.

### Backup Your Database

Press **Backup Database** to create a timestamped copy of your database:
```
~/.pjourney/pjourney_backup_YYYYMMDD_HHMMSS.db
```

Do this before making large changes or periodically as a precaution.

### Vacuum the Database

Press **Vacuum Database** to optimise your database file. This reclaims space after deletions and keeps things tidy. It is safe to run at any time.

### Cloud Sync (Dropbox)

The Cloud Sync section lets you back up and restore your database to and from Dropbox.

**Linking your account**

Press **Link Account**. pjourney will open a Dropbox authorisation page in your browser. Sign in, authorise pjourney, then paste the code shown into the dialog.

Once linked the status line shows your Dropbox account name, selected backup folder (if set), and the last sync time.

**Selecting a backup folder**

Press **Select Folder** to browse your Dropbox and choose where backups are stored. You can also create a new folder from within the browser.

**Uploading a backup**

Press **Sync Now** to upload a timestamped copy of your database to the selected Dropbox folder:
```
<remote_folder>/pjourney_YYYYMMDD_HHMMSS.db
```

**Restoring from a backup**

Press **Restore** to browse your cloud backups and download one to replace the local database. pjourney saves a local safety copy before overwriting, then verifies the downloaded file is a valid SQLite database. Restart the app after a restore to reconnect to the database.

**Disconnecting**

Press **Disconnect** to revoke pjourney's Dropbox access and remove stored credentials. Your cloud backups are not deleted.

### User Management

- **Create User** — Add a new account. Each user has their own isolated inventory.
- **Delete User** — Remove an account. You cannot delete the account you are currently logged in as.

---

## Keyboard Shortcuts — Full Reference

### Navigation

| Screen | Key | Action |
|--------|-----|--------|
| Dashboard | `c` | Go to Cameras |
| Dashboard | `l` | Go to Lenses |
| Dashboard | `f` | Go to Film Stock |
| Dashboard | `r` | Go to Rolls |
| Dashboard | `a` | Go to Admin |
| Dashboard | `q` | Quit |
| Any screen | `Esc` | Go back |

### Tables (All Inventory Screens)

| Key | Action |
|-----|--------|
| `j` or `↓` | Move cursor down |
| `k` or `↑` | Move cursor up |
| `g` | Jump to top |
| `G` | Jump to bottom |
| `Ctrl+D` | Page down |
| `Ctrl+U` | Page up |

### Cameras, Lenses, Film Stock

| Key | Action |
|-----|--------|
| `a` | Add new item |
| `e` | Edit selected item |
| `d` | Delete selected item |
| `Enter` | Open detail view |

### Rolls

| Key | Action |
|-----|--------|
| `n` | Create new roll |
| `l` | Load roll into camera |
| `s` | Advance roll status |
| `f` | View frames for this roll |
| `i` | View development info |
| `d` | Delete roll |

### Camera Issues

| Key | Action |
|-----|--------|
| `a` | Log a new issue |
| `r` | Mark selected issue as resolved |

Deleting an issue requires clicking the **Delete Issue** button (no keyboard shortcut).

### Lens Notes

| Key | Action |
|-----|--------|
| `a` | Add a new note |
| `e` | Edit selected note |
| `d` | Delete note |

### Frames

| Key | Action |
|-----|--------|
| `e` | Edit selected frame |

---

## Tips

- **Log frames as you shoot.** Your memory of what settings you used fades fast. Even jotting the subject and approximate settings while the roll is in the camera pays off later.
- **Use the status filter.** The Rolls screen filter buttons (Fresh, Loaded, Shooting, etc.) let you instantly find rolls at a particular stage without scrolling through your whole history.
- **Camera issues are a maintenance diary.** Even if something is not broken, logging a quirk — like a sticky advance lever that clears up in the cold — helps you remember it later.
- **Lens notes are freeform.** Use them for anything: optimal apertures, focus calibration offsets, filter notes, repair receipts, or shooting tips you discovered.
- **Back up regularly.** The Admin screen makes it one button press. Do it before you delete anything significant. Connect Dropbox for off-machine backups with **Sync Now**.
- **Multiple users.** If you share the machine with another photographer, each person can have their own account with completely separate gear and roll history.

---

## Data Storage

Your database lives on your machine at:

```
~/.pjourney/pjourney.db
```

Local backups are saved in the same directory. If you connect a Dropbox account via the Admin screen, pjourney will also upload timestamped backup copies to the Dropbox folder you choose. No data is sent anywhere unless you explicitly press **Sync Now** or **Restore**.

---

*pjourney — keep the record, cherish the roll.*
