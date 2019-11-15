# This takes in a .json formatted configuration file containing 
# names and extensions of the layers to process along with the 
# filenames of the new and old board fab files. This assumes 
# gerbers are supplied in two .zip files each containing a 
# directory called Gerber/
# Requires gerbv to be installed at the system level. This 
# works fine with gerbv installed using homebrew on Mac, haven't 
# tested on linux but should be fine there too. Fuck windows, 
# I could write this smarter to deal with backslashes and maybe
# works on Windows,but I'm lazy.

import json
import os
import glob
import zipfile
import shutil
from fpdf import FPDF
from PIL import Image, ImageFont, ImageDraw

class gerbv_project():
    """ This is necessary because there doesn't seem to be a command line
    switch to turn on XOR view in gerbv, and it will default to stacking. """
    def __init__(self):
        self.filetext = ("(gerbv-file-version! \"2.0A\")\n"
                        "(define-layer! 1 (cons 'filename \"[OLD_FILE_NAME]\")\n"
                        "(cons 'visible #t)\n"
                        "(cons 'color #(65535 35392 32566))\n"
                        ")\n"
                        "(define-layer! 0 (cons 'filename \"[NEW_FILE_NAME]\")\n"
                        "(cons 'visible #t)\n"
                        "(cons 'color #(32768 37136 65535))\n"
                        ")\n"
                        "(define-layer! -1 (cons 'filename \"[GERBER_PATH]\")\n"
                        "(cons 'color #(0 0 0))\n"
                        ")\n"
                        "(set-render-type! 1)\n")

    def set_old_filename(self, filename):
            if "[OLD_FILE_NAME]" in self.filetext:
                self.filetext = self.filetext.replace("[OLD_FILE_NAME]",
                                                        filename)
            else:
                raise ValueError("Old File already set!")

    def set_new_filename(self, filename):
            if "[NEW_FILE_NAME]" in self.filetext:
                self.filetext = self.filetext.replace("[NEW_FILE_NAME]",
                                                        filename)
            else:
                raise ValueError("New File already set!")

    def write_project_file(self, filename = None):
        if not filename:
            filename = "temp_project.gvp"
        with open(filename, 'w') as fid:
            fid.write(self.filetext)
        return filename

class gerber_diff():
    def __init__(self, config_file_name):
        #self.temp_dir_path = os.cwd
        self.gvp_filename = None
        self.layers = {}

        # define paths for temp folders to hold old and new gerber data
        self.root_folder = os.getcwd()
        self.temp_folder_path = self.root_folder + "/temp/"
        if os.path.exists(self.temp_folder_path):
            shutil.rmtree(self.temp_folder_path, ignore_errors=True)
        os.mkdir(self.temp_folder_path)
        self.old_folder_path = self.temp_folder_path + "old/"
        self.new_folder_path = self.temp_folder_path + "new/"
        self.old_gerber_path = self.old_folder_path + "Gerber/"
        self.new_gerber_path = self.new_folder_path + "Gerber/"
        self.image_path = self.temp_folder_path +"diffs/"
        os.mkdir(self.image_path)

        # load project config data
        with open(config_file_name) as config_file:
            config_file_data = json.load(config_file)

        # load layer info into a dictionary
        for item in config_file_data["layers"]:
            self.layers[item["extension"]] = item["layer"]
        self.layer_order = config_file_data["layer_order"]

        # extract the old and new archives into the temp folder
        self.old_zip_filename = config_file_data['old_archive']
        self.new_zip_filename = config_file_data['new_archive']
        with zipfile.ZipFile(self.old_zip_filename, 'r') as old_zip_fid:
            old_zip_fid.extractall(self.old_folder_path)
        with zipfile.ZipFile(self.new_zip_filename, 'r') as new_zip_fid:
            new_zip_fid.extractall(self.new_folder_path)

        self.output_file_name = self.root_folder + "/" + config_file_data['output_file']

    def get_gerber(self, path, extension):
        filelist = glob.glob(path+"/*"+extension)
        if len(filelist)<1:
            raise KeyError("Layer Not Found!")
        elif len(filelist)>1:
            raise KeyError("Duplicate Layer Detected!")
        else:
            return filelist[0]

    def label_image(self, image_file, label_text):
        im = Image.open(image_file)
        txt = ImageFont.truetype("Courier.ttf", size=75)
        d = ImageDraw.Draw(im)

        loc = (0,0)
        color = "white"
        d.text(loc, label_text, font=txt, fill=color)

        im.save(image_file)

    def get_image_filename(self, active_layer):
        image_filename = self.image_path + "_".join(self.layers[active_layer].split(" ")) + ".png"
        return image_filename

    def diff_layer(self, active_layer):
        old_filename = self.get_gerber(self.old_gerber_path, active_layer)
        new_filename = self.get_gerber(self.new_gerber_path, active_layer)
        image_filename = self.get_image_filename(active_layer)
        self.create_temp_project(old_filename, new_filename)
        command_string = "gerbv -a -x png -D 600 -o {} -p {}".format(
                                                            image_filename,
                                                            self.gvp_filename)
        os.system(command_string)

        self.label_image(image_filename, self.layers[active_layer])

    def make_pdf(self):
        image_list = [self.get_image_filename(item) for item in self.layer_order]
        cover = Image.open(str(image_list[0]))
        width, height = cover.size
        pdf = FPDF(unit = "pt", format = [width, height])

        for page in image_list:
            pdf.add_page()
            pdf.image(str(page), 0, 0)

        pdf.output(self.output_file_name + ".pdf", "F")

    def run_diff(self):
        for layer in self.layers.keys():
            print("Processing {}".format(self.layers[layer]))
            self.diff_layer(layer)
        self.make_pdf()
        shutil.rmtree(self.temp_folder_path, ignore_errors=True)

    def create_temp_project(self, old_file, new_file):
        gvp = gerbv_project()
        gvp.set_old_filename(old_file)
        gvp.set_new_filename(new_file)
        self.gvp_filename = gvp.write_project_file(self.temp_folder_path + "temp_project.gvp")

if __name__ == "__main__":
    gd = gerber_diff("mlb_config.json")
    gd.run_diff()
