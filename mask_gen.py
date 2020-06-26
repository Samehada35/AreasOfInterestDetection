import fitz
import numpy as np
import cv2
import os
import re
import pdfplumber
import sys
import json
import argparse
from xml_utils import *

#Generates the images with masks applied to it
def generate_masked_images(mask_path,img_path,mask_img_path):
    #Range of colors required to extract every part of the mask
    lower_white = np.array([205, 205, 205])
    upper_white = np.array([255, 255, 255])
    lower_dark_gray = np.array([10, 10, 10])
    upper_dark_gray = np.array([130, 130, 130])
    lower_gray = np.array([150, 150, 150])
    upper_gray = np.array([200, 200, 200])

    #We read the image and the mask from the paths given
    image = cv2.imread(img_path)
    mask = cv2.imread(mask_path)

    #We then extract the different parts of the masks using the color ranges above
    text_mask = cv2.cvtColor(cv2.bitwise_not(cv2.Canny(cv2.inRange(mask, lower_white, upper_white),30,200)),cv2.COLOR_GRAY2RGB)
    table_mask = cv2.cvtColor(cv2.bitwise_not(cv2.Canny(cv2.inRange(mask, lower_gray, upper_gray),30,200)),cv2.COLOR_GRAY2RGB)
    image_mask = cv2.cvtColor(cv2.bitwise_not(cv2.Canny(cv2.inRange(mask, lower_dark_gray, upper_dark_gray),30,200)),cv2.COLOR_GRAY2RGB)

    #We detect in every part of the mask where the color is black (meaning there's either an image,table or text)
    text_ind = np.where(text_mask == [0,0,0])
    table_ind = np.where(table_mask == [0,0,0])
    image_ind = np.where(image_mask == [0,0,0])

    #We replace the grayscale colors by blue,green and red respectively for texts,tables and images
    text_mask[text_ind[0],text_ind[1],:] = [255,0,0]
    table_mask[table_ind[0],table_ind[1],:] = [0,255,0]
    image_mask[image_ind[0],image_ind[1],:] = [0,0,255]

    #We finally combine the modified mask with the image with a bitwise and operation
    mask_img = cv2.bitwise_and(image,text_mask)
    mask_img = cv2.bitwise_and(mask_img,table_mask)
    mask_img = cv2.bitwise_and(mask_img,image_mask)

    #We save the result in the given path
    cv2.imwrite(mask_img_path, mask_img)

#Generates masks for every page of a single document
def generate_mask(doc,doc_plumber,doc_name):
    global args

    for page in doc:
        print("Page {}/{}".format(page.number+1,doc.pageCount))

        #Initialisations of output paths
        mask_path = "./masks/mask_{}_{}.jpg".format(doc_name,page.number)
        img_path = "./images/{}_{}.jpg".format(doc_name,page.number)
        mask_img_path = "./masked_images/masked_{}_{}.jpg".format(doc_name,page.number)
        json_path = "./json/{}_{}.json".format(doc_name,page.number)
        html_path = "./html/{}_{}.html".format(doc_name,page.number)
        xml_path = "./xml/{}_{}.xml".format(doc_name,page.number)
        page_img = page.getPixmap(alpha=False,annots=False)
        page_height = page_img.height
        page_width = page_img.width

        page_data_json = []
        page_data_xml = construct_xml("{}_{}.jpg".format(doc_name,page.number),"{}\\images\\{}_{}.jpg".format(os.getcwd(),doc_name,page.number),page_width,page_height)
        mask = np.zeros([page_height,page_width])
        html = page.getText("html")

        #For images, we search for the presence of <img/> tag using the corresponding html of the page
        img_tags = re.findall(r'<img[^>]+>',html)
        for tag in img_tags:
            #We extract the style attribute from the <img/> tag
            style_attribute = re.search('style="([^"]*)"',tag,re.IGNORECASE).group(1)
            #And only keep the attributes top, left, width and height
            attributes = [a for a in style_attribute.split(";") if "top" in a or "left" in a or "width" in a or "height" in a]
            x0,x1,y1,y0 = [None]*4
            for a in attributes:
                att = a.split(":")
                att[1] = re.sub("\D+","",att[1])
                if att[0] == "top":
                    y0 = int(att[1])
                elif att[0] == "left":
                    x0 = int(att[1])
                elif att[0] == "width":
                    x1 = int(att[1])
                elif att[0] == "height":
                    y1 = int(att[1])
            #We add the width to x1, same for y1
            x1 += x0
            y1 += y0

            #We correct the values to avoid errors
            if x0 < 0:
                x0 = 0
            if y0 < 0:
                y0 = 0

            if x0>page_width or x1>page_width or y0>page_height or y1>page_height or x1<0 or y1<0:
                continue
            if x0 < 0:
                x0=0
            if y0 < 0:
                y0 = 0
            #We fill the rectangle delimited with x0,x1,y0,y1 with the corresponding color
            mask[y0:y1,x0:x1] = 180
            construct_object_xml(page_data_xml,"image",x0,x1,y0,y1)

            if args.json:
                page_data_json.append({"name" : "image",
                                       "bndbox" : { "xmin" : x0,
                                                    "xmax" : x1,
                                                    "ymin" : y0,
                                                    "ymax" : y1
                                      }})
        #We then generate the mask for texts
        for b in page.getText("blocks"):
            if not re.search(r"^[\s\n\r\t]+$",b[4]):
                x0 = int(b[0])
                x1 = int(b[2])
                y0 = int(b[1])
                y1 = int(b[3])
            if x0>page_width or x1>page_width or y0>page_height or y1>page_height or x1<0 or y1<0:
                continue
            if x0 < 0:
                x0 = 0
            if y0 < 0:
                y0 = 0


            mask[y0:y1,x0:x1] = 255
            construct_object_xml(page_data_xml,"text",x0,x1,y0,y1)
            if args.json:
                page_data_json.append({"name" : "text",
                                       "bndbox" : { "xmin" : x0,
                                                    "xmax" : x1,
                                                    "ymin" : y0,
                                                    "ymax" : y1
                                      }})

        #Same thing with tables
        p = doc_plumber.pages[page.number]
        for b in p.find_tables():
            b = b.bbox
            x0 = int(b[0])
            x1 = int(b[2])
            y0 = int(b[1])
            y1 = int(b[3])

            if x0>page_width or x1>page_width or y0>page_height or y1>page_height or x1<0 or y1<0:
                continue
            if x0 < 0:
                x0 = 0
            if y0 < 0:
                y0 = 0

            mask[y0:y1,x0:x1] = 100
            construct_object_xml(page_data_xml,"table",x0,x1,y0,y1)

            if args.json:
                page_data_json.append({"name" : "table",
                                       "bndbox" : { "xmin" : x0,
                                                    "xmax" : x1,
                                                    "ymin" : y0,
                                                    "ymax" : y1
                                      }})
        #We write the generated mask and the image
        cv2.imwrite(mask_path, mask)
        page_img.writeImage(img_path)

        #We combine the mask and the image
        generate_masked_images(mask_path,img_path,mask_img_path)

        #We generate the annotation file for the page
        save_xml(page_data_xml,xml_path)

        #If the user has specified one of the optionnal arguments, we generate a json file and/or an html file
        if args.json:
            with open(json_path, 'w') as f:
                json.dump(page_data_json, f)

        if args.html:
            with open(html_path,"w") as f:
                f.write(html)


def main():
    global args
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", help="absolute or relative path of the file you want to generate a mask for")
    parser.add_argument("--json", help="Generate annotations in json format",action="store_true")
    parser.add_argument("--html", help="Generate input files in html format",action="store_true")
    args = parser.parse_args()

    doc_name = args.filename
    doc_plumber = pdfplumber.open(doc_name)
    doc = fitz.open(doc_name)
    doc_name = os.path.splitext(os.path.basename(doc_name))[0]

    print("Generating masks for file {}".format(doc_name))
    generate_mask(doc,doc_plumber,doc_name)

args = None
main()
