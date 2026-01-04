README: Photo Workflow Automation (HDR Production & Pano Preparation)

This program automates the organization and batch processing of large quantities of RAW images. It is specifically designed to handle the critical steps before stitching a panorama: sorting sequences, producing intermediate HDR files, and securing a consistent fallback image set.

What does this program do?
1.	Sort & Clean up (with Fallback): Automatically groups RAW files into sequences (stacks). Only the first photo of each stack (and every individual loose photo) remains in the main folder.
·	The Big Advantage: Not only does this provide a clean visual overview, but it also ensures you have a complete set of images ready to stitch a standard (non-HDR) panorama immediately, should the HDR version prove unusable (e.g., due to 'ghosting' from moving branches or clouds).
1.	Batch HDR Production: Automatically merges entire folders of sequences into high-quality 32-bit DNG (via HDRmerge) or TIFF files (via Enfuse).
2.	Panorama Preparation: Moves all completed HDR results to a folder named 'Verzamelde_HDR_bestanden'. This folder is placed one level above your working directory, so your results are instantly ready for your panorama software.


Essential Settings
·	Stack Size (Tab 1):
Determines how the script divides photos into sequences. 'Auto' uses time and exposure. Use 'Fixed at 3, 5, or 7' if you photographed many sequences in very quick succession to prevent multiple stacks from being merged into a single folder.
·	Cleanup (Tab 3):
'Remove RAW sequences' deletes the subfolders containing the original RAW files once the HDR files have been collected. This saves significant disk space. The fallback photos in your main folder are always preserved.


Installation on Linux Desktop (Arch Linux)
1.	Install Required Software:
Open your terminal and run the following command to install all dependencies:

sudo pacman -S pyside6 perl-image-exiftool darktable hugin enblend-enfuse hdrmerge xdg-desktop-portal-kde

(Use xdg-desktop-portal-gnome if you are using the GNOME desktop environment instead of KDE).

1.	Prepare Files:
·	Save the script (e.g., as workflow_hdr.py).
·	Crucial: Place your Darktable processing profile named 'oppepper.xmp' in the same folder as the script. This file is required for the correct development of TIFF files.

1.	Execution:
Make the script executable and start it using these commands:

chmod +x workflow_hdr.py
./workflow_hdr.py


System Requirements & Technology
·	File System: Optimized for Btrfs. Uses 'reflinks' to copy files instantly without consuming additional disk space. Also works on Ext4 via standard copy actions.
·	Processor: Fully utilizes multicore processors (like the Ryzen 3600) for aligning and merging images.
·	GPU Acceleration: Supports OpenCL/Rusticl for fast RAW development via the video card.
·	Flawless Edges: Utilizes the '-C' (auto-crop) flag during alignment to prevent incorrect color borders at the edges of the processed images.

