# Vitalux – Changelog

Every Vitalux release is documented here. The Updates page displays
what has changed before you install a new version and keeps the changelog
of installed and earlier releases available offline.

## [v0.9.3.60] - 2026-10-17
- Fixed invisible hardware warning thresholds: the clipped native QSpinBox editor is replaced by a separately laid out number input and visible unit for reliable rendering on KDE/Wayland.
- Thresholds stay editable with arrow keys, mouse wheel, range validation, and persisted settings.
- Preserved compact widths and column alignment and expanded visual and editing regression tests.

## [v0.9.3.59] - 2026-10-17
- Reverted the problematic recent drop-down styling and restored the previous controls with a darker selection area on the right.
- Restored readable selection text, including full version numbers in the changelog drop-down.
- Hardware-warning fields display their values and units again, with consistent alignment.
- Updated graphical tests for the restored controls.

## [v0.9.3.58] - 2026-10-17
- All warning-value controls now line up in one common column regardless of label length.
- Narrower warning values without up/down buttons; keyboard, arrow-key and mouse-wheel input remain available.
- More compact drop-downs with no arrows or separate arrow compartments.
- Closed drop-down fields are painted in the active Vitalux theme, independent of the host KDE/Qt style.
- Popup lists, borders and scroll areas explicitly use their current theme's background and text colors.
- Updated tests and README.

## [v0.9.3.57] - 2026-10-17
- Slightly narrower drop-downs with matching custom chevrons for each color scheme.
- Theme-matched popup lists without native black menu strips above and below the items.
- CPU, GPU, RAM and system drive thresholds now sit uniformly right next to their labels.
- Reordered custom accent actions: Edit, Delete, Custom color.
- Updated settings tests and README.

## [v0.9.3.56] - 2026-10-17
- Saved custom accent colors now support editing both the name and color value through a new Edit button, without creating duplicate entries.
- A separate Delete button appears alongside Edit only when a saved custom color is selected.
- All drop-down selectors now match Dark, Light, Glass, Black Glass and Minimalist themes, including the SMART drive selector, with a very small width reduction.
- Temperature and usage alert input fields now follow their labels on the right, retaining compact centered values.
- The update changelog displays only the selected UI language, either German or English.
- Updated the integrated tutorial and GitHub README to cover the improved controls.

## [v0.9.3.55] - 2026-10-17
- Redesigned the drop-down menus with consistent themed popup backgrounds, removing unwanted dark bands at their top and bottom.
- Moved the compact, center-aligned temperature and usage alert fields to the left of their labels, without changing the card size.
- Added fully translated English changelogs for installed versions and upcoming updates; switching between German and English refreshes both.
- Updated the in-app guide and README with relevant display, alert, accent-color, and changelog improvements.

## [v0.9.3.54] - 2026-10-17
- Unified the checkbox appearance with visible check marks across charts, settings, and benchmarks.
- Made alert threshold input fields narrower, with centered values and unchanged card dimensions.
- Custom accent colors can be named, saved, and removed using the X next to the color selector.
- Added a changelog to Vitalux: view upcoming changes before updating and browse version history afterwards.
- GitHub releases now automatically use the changes listed in the changelog.

## [v0.9.3.53] - 2026-10-17
- Improved the automatic restoration of the previous AppImage on the first restart after an update.
- Verified recovery for restarts originating from older Vitalux versions.

## [v0.9.3.52] - 2026-10-17
- Removed problematic explicit mouse grabs in the Wayland layout editor and improved crash diagnostics.
- Added individually designed SVG artwork in the six preset accent colors; the original logo remains for distribution and custom colors.
- Added recovery of the immediately preceding version, with AppImage and ZIP tests.

## [v0.9.3.51] - 2026-10-17
- The distribution logo can now be hidden independently using an X in the layout editor and restored with "Add tiles".
- Added Save, Discard, and Undo for distribution-logo visibility.
- Added initial theme-based recoloring of the Vitalux symbol and wordmark, later replaced with individually designed SVG color variants.
