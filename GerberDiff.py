# This takes in a .json formatted configuration file containing 
# names and extensions of the layers to process along with the 
# filenames of the new and old board fab files. This assumes 
# gerbers are supplied in two .zip files each containing a 
# directory called Gerber/


import zipfile
import fnmatch
import argparse
import sys

from fpdf import FPDF
from io import BytesIO
from PIL import Image
from gerber import load_layer_data
from gerber.render import RenderSettings
from gerber.render import theme
from gerber.render.cairo_backend import GerberCairoContext


class GerberDiff():
    old_color = RenderSettings(color=theme.COLORS['blue'], alpha=0.5)
    new_color = RenderSettings(color=theme.COLORS['red'], alpha=0.4)
    bg_color = RenderSettings(color=theme.COLORS['black'], alpha=1)

    def __init__(self, old_archive, new_archive):
        self.layer_images = {}
        self.old_gerbers = self._extractGerbers(old_archive)
        self.new_gerbers = self._extractGerbers(new_archive)
        self.extensionList = self.listExtensions()

    def listExtensions(self):
        # report unique extensions
        unique_to_old = self.old_gerbers.keys() - self.new_gerbers.keys()
        unique_to_new = self.new_gerbers.keys() - self.old_gerbers.keys()
        if len(unique_to_old)>0:
            print("Unique extensions found in old gerber package: %s"%unique_to_old)
        if len(unique_to_new)>0:
            print("Unique extensions found in new gerber package: %s"%unique_to_new)
        return list(self.old_gerbers.keys() & self.new_gerbers.keys())

    def executeDiff(self):
        for key in self.extensionList:
            self.layer_images[key] = self._drawLayer(self.old_gerbers[key],
                                                    self.new_gerbers[key],
                                                    key)
            print("Processed %s"%key)
 
    def makePDF(self, image_list=None, output_filename = "diff.pdf"):
        if image_list is None:
            image_list = self.extensionList
        #find largest dimensions
        max_w = 0
        max_h = 0
        for layer in image_list:
            with Image.open(self.layer_images[layer]) as im:
                width, height = im.size
                max_w = [max_w, width][width > max_w]
                max_h = [max_h, height][height > max_h]
        pdf = FPDF(unit = "pt", format = [max_w, max_h])

        for layer in image_list:
            pdf.add_page()
            pdf.set_text_color(255,255,255)
            pdf.set_font("Helvetica", "B", 32,)
            pdf.image(self.layer_images[layer], 0, 0)
            pdf.cell(0,0, str(layer))\

        pdf.output(output_filename, "F")

    def _extractGerbers(self, archive_name):
        res = {}
        with zipfile.ZipFile(archive_name) as zf:
            fn_list = filter(lambda filename: fnmatch.fnmatch(filename, 
                                                            "Gerber/*.G*"),
                            zf.namelist())
            for filename in fn_list:
                extension = filename.split(".")[1]
                with zf.open(filename) as filedata:
                    res[extension] = filedata.read()
        return res

    def _drawLayer(self, layer_1, layer_2, label):
        ctx = GerberCairoContext()
        l1 = load_layer_data(layer_1.decode())
        l2 = load_layer_data(layer_2.decode())
        ctx.render_layer(l1,
                        settings=self.old_color,
                        bgsettings=self.bg_color)
        ctx.render_layer(l2,
                        settings=self.new_color,
                        bgsettings=self.bg_color)
        return BytesIO(ctx.dump_str())

def parse_args(args):
    parser = argparse.ArgumentParser(description="Generate a Gerber diff from two .zip files")
    parser.add_argument("zip1")
    parser.add_argument("zip2")
    parser.add_argument("-n", "--name", type=str,
                        help="A file name for .pdf output")
    parser.add_argument("-l", "--list", type=str, nargs="+",
                        help="A sequence of layer extensions to plot in order")
    return parser.parse_args(args)

def main():
    args = parse_args(sys.argv[1:])
    gd = GerberDiff(args.zip1, args.zip2)
    gd.executeDiff()
    gd.makePDF(image_list = args.list, output_filename=args.name)

if __name__ == "__main__":
    main()
