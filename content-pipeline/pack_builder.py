"""Shared packaging logic: turn a list of raw images into a Gumroad-ready
pack (print JPEGs + 9:16 wallpaper crops + README, zipped). Used both by
generate_product_pack.py (the old fixed-list flow) and process_queue.py
(building a pack once enough review-queue images for it are approved)."""

import os
import subprocess


def assemble_pack(images, name, theme, slug, out_dir):
    """images: list of {"id": str, "raw_path": str}, in the order they
    should appear. Returns (pack_dir, zip_path)."""
    pack_dir = os.path.join(out_dir, f"gumroad-pack-{slug}")
    print_dir = os.path.join(pack_dir, "print")
    wallpaper_dir = os.path.join(pack_dir, "wallpaper")
    os.makedirs(print_dir, exist_ok=True)
    os.makedirs(wallpaper_dir, exist_ok=True)

    for i, img in enumerate(images, start=1):
        num = f"{i:02d}"
        raw_path = img["raw_path"]
        print_jpg = os.path.join(print_dir, f"{num}-{img['id']}.jpg")
        wallpaper_jpg = os.path.join(wallpaper_dir, f"{num}-{img['id']}-wallpaper.jpg")

        subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "92", raw_path, "--out", print_jpg],
                        check=True, capture_output=True)

        dim = subprocess.run(["sips", "-g", "pixelHeight", "-g", "pixelWidth", raw_path],
                              check=True, capture_output=True, text=True).stdout
        height = int([l for l in dim.splitlines() if "pixelHeight" in l][0].split(":")[1].strip())
        crop_width = round(height * 9 / 16)
        subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "92",
                         "-c", str(height), str(crop_width), raw_path, "--out", wallpaper_jpg],
                        check=True, capture_output=True)

    readme_path = os.path.join(pack_dir, "README.txt")
    with open(readme_path, "w") as f:
        f.write(f"{name}\n{theme}\n\n")
        f.write("Thanks for downloading.\n\n")
        f.write("WHAT'S INSIDE\n")
        f.write("- print/       high-resolution images (2:3 ratio), ready to print\n")
        f.write("- wallpaper/   the same scenes, cropped to 9:16 for phone lock screens/wallpapers\n\n")
        f.write("PRINT SIZES\n")
        f.write("The 2:3 ratio matches standard frame sizes: 4x6in, 8x12in, 12x18in, 16x24in.\n")
        f.write("For best quality, don't print larger than 16x24in from these files.\n\n")
        f.write("Enjoy, and tag @farawayfolio if you share where you put them.\n")

    zip_path = os.path.join(out_dir, f"Faraway-Folio-{name.split(', ')[-1].replace(' ', '-')}.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)
    subprocess.run(["zip", "-r", zip_path, f"gumroad-pack-{slug}/print", f"gumroad-pack-{slug}/wallpaper",
                     f"gumroad-pack-{slug}/README.txt"], cwd=out_dir, check=True, capture_output=True)

    return pack_dir, zip_path
