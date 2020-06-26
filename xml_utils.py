from xml.etree.ElementTree import Element, SubElement, Comment, tostring,ElementTree

#Generates a basic xml in Pascal VOC format for annotation
def construct_xml(filename,path,we,he,de=0):
    page_data_xml =Element("annotation")

    e = SubElement(page_data_xml,"filename")
    e.text = filename

    e = SubElement(page_data_xml,"path")
    e.text = path

    e = SubElement(page_data_xml,"folder")
    e.text = "images"

    e = SubElement(page_data_xml,"source")
    f = SubElement(e,"database")
    f.text = "Unknown"

    e = SubElement(page_data_xml,"size")
    f = SubElement(e,"width")
    g = SubElement(e,"height")
    h = SubElement(e,"depth")
    f.text = str(we)
    g.text = str(he)
    h.text = str(de)

    e = SubElement(page_data_xml,"segmented")
    e.text = "0"

    return page_data_xml

#Adds an <object> tag to the pascal voc file corresponding to a text/image/table in the original document
def construct_object_xml(root,label,x0,x1,y0,y1):
    e = SubElement(root,"object")

    f = SubElement(e,"name")
    f.text = label

    f = SubElement(e,"pose")
    f.text = "Unspecified"

    f = SubElement(e,"truncated")
    f.text = "0"

    f = SubElement(e,"difficult")
    f.text = "0"

    f = SubElement(e,"bndbox")
    g = SubElement(f,"xmin")
    g.text = str(x0)
    g = SubElement(f,"xmax")
    g.text = str(x1)
    g = SubElement(f,"ymin")
    g.text = str(y0)
    g = SubElement(f,"ymax")
    g.text = str(y1)

    return e

def save_xml(xml,path):
    ElementTree(xml).write(path)
