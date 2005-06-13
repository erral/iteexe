# ===========================================================================
# eXe 
# Copyright 2004-2005, University of Auckland
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
# ===========================================================================
"""
Exports an eXe package as a SCORM package
"""

import logging
import gettext
import re
import os
from zipfile                import ZipFile, ZIP_DEFLATED
from exe.webui              import common
from exe.webui.blockfactory import g_blockFactory
from exe.webui.titleblock   import TitleBlock
from exe.engine.error       import Error
from exe.engine.path        import Path, TempDirPath
from exe.export.pages       import Page, uniquifyNames
from exe.engine.uniqueidgenerator  import UniqueIdGenerator

log = logging.getLogger(__name__)
_   = gettext.gettext


# ===========================================================================
class Manifest(object):
    """
    Represents an imsmanifest xml file
    """
    def __init__(self, config, outputDir, package, pages):
        """
        Initialize
        'outputDir' is the directory that we read the html from and also output
        the mainfest.xml 
        """
        self.outputDir    = outputDir
        self.package      = package
        self.idGenerator  = UniqueIdGenerator(package.name, config.exePath)
        self.pages        = pages
        self.itemStr      = ""
        self.resStr       = ""


    def save(self):
        """
        Save a imsmanifest file to self.outputDir
        """
        filename = "imsmanifest.xml"
        out = open(self.outputDir/filename, "w")
        out.write(self.createXML().encode('utf8'))
        out.close()
        

    def createXML(self):
        """
        returning XLM string for manifest file
        """
        manifestId = self.idGenerator.generate()
        orgId      = self.idGenerator.generate()
        
        xmlStr = u"""<?xml version="1.0" encoding="UTF-8"?>
        <manifest identifier="%s" 
        xmlns="http://www.imsglobal.org/xsd/imscp_v1p1" 
        xmlns:imsmd="http://www.imsglobal.org/xsd/imsmd_v1p2" 
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
        """ % manifestId 

        xmlStr += "\n "
        xmlStr += "xsi:schemaLocation=\"http://www.imsglobal.org/xsd/"
        xmlStr += "imscp_v1p1 imscp_v1p1.xsd "        
        xmlStr += "http://www.imsglobal.org/xsd/imsmd_v1p2 imsmd_v1p2p2.xsd\""
        xmlStr += "> \n"
        xmlStr += "<metadata> \n"
        xmlStr += " <schema>IMS Content</schema> \n"
        xmlStr += " <schemaversion>1.1.3</schemaversion> \n"
        xmlStr += "</metadata> \n"
        xmlStr += "<organizations default=\""+orgId+"\">  \n"
        xmlStr += "<organization identifier=\""+orgId
        xmlStr += "\" structure=\"hierarchical\">  \n"
        title  = unicode(self.package.root.title)
        xmlStr += "<title>"+title+"</title>\n"
        
        depth = 0
        for page in self.pages:
            while depth >= page.depth:
                self.itemStr += "</item>\n"
                depth -= 1
            self.genItemResStr(page)
            depth = page.depth

        while depth >= 1:
            self.itemStr += "</item>\n"
            depth -= 1

        xmlStr += self.itemStr
        xmlStr += "</organization>\n"
        xmlStr += "</organizations>\n"
        xmlStr += "<resources>\n"
        xmlStr += self.resStr
        xmlStr += "</resources>\n"
        xmlStr += "</manifest>\n"
        return xmlStr
        
            
    def genItemResStr(self, page):
        """
        Returning xml string for items and resources
        """
        itemId   = "ITEM-"+unicode(self.idGenerator.generate())
        resId    = "RES-"+unicode(self.idGenerator.generate())
        filename = page.name+".html"
            
        
        self.itemStr += "<item identifier=\""+itemId+"\" isvisible=\"true\" "
        self.itemStr += "identifierref=\""+resId+"\">\n"
        self.itemStr += "    <title>"+unicode(page.node.title)+"</title>\n"
        
        self.resStr += "<resource identifier=\""+resId+"\" "
        self.resStr += "type=\"webcontent\" "

        self.resStr += "href=\""+filename+"\"> \n"
        self.resStr += """\
    <file href="%s"/>
    <file href="content.css"/>""" %filename
        self.resStr += "\n"
        fileStr = ""

        for resource in page.node.getResources():
            fileStr += "    <file href=\""+resource+"\"/>\n"

        self.resStr += fileStr
        self.resStr += "</resource>\n"


# ===========================================================================
class IMSPage(Page):
    """
    This class transforms an eXe node into a SCO 
    """
    def save(self, outputDir):
        """
        This is the main function.  It will render the page and save it to a
        file.  
        'outputDir' is the name of the directory where the node will be saved to,
        the filename will be the 'self.node.id'.html or 'index.html' if
        self.node is the root node. 'outputDir' must be a 'Path' instance
        """
        out = open(outputDir/self.name+".html", "w")
        out.write(self.render().encode('utf8'))
        out.close()

    def render(self):
        """
        Returns an XHTML string rendering this page.
        """
        html  = common.docType()
        html += "<html xmlns=\"http://www.w3.org/1999/xhtml\">\n"
        html += "<head>\n"
        html += "<meta http-equiv=\"content-type\" content=\"text/html; "
        html += " charset=UTF-8\" />\n";
        html += "<title>"+_("eXe")+"</title>\n"
        html += "<style type=\"text/css\">\n"
        html += "@import url(content.css);\n"
        html += "</style>\n"
        for idevice in self.node.idevices:
            if idevice.title == "Quiz Test":
                html += "<script language=\"javascript\" "
                html += "src=\"quizForWeb.js\"></script>\n"
                break
            
        html += "</head>\n"
        html += "<body>\n"
        html += "<div id=\"outer\">\n"
        html += "<div id=\"main\">\n"
        title = TitleBlock(None, self.node._title)
        html += title.renderView(self.node.package.style)

        for idevice in self.node.idevices:
            block = g_blockFactory.createBlock(None, idevice)
            if not block:
                log.critical("Unable to render iDevice.")
                raise Error("Unable to render iDevice.")
            html += block.renderView(self.node.package.style)

        html += "</div>\n"
        html += "</div>\n"
        html += "</body></html>\n"
        return html

        
# ===========================================================================
class IMSExport(object):
    """
    Exports an eXe package as a SCORM package
    """
    def __init__(self, config, styleDir, filename):
        """ Initialize
        'styleDir' is the directory from which we will copy our style sheets
        (and some gifs)
        """
        self.config     = config
        self.imagesDir  = config.webDir/"images"
        self.scriptsDir = config.webDir/"scripts"
        self.styleDir   = Path(styleDir)
        self.filename   = Path(filename)
        self.pages      = []


    def export(self, package):
        """ 
        Export SCORM package
        """
        # First do the export to a temporary directory
        outputDir = TempDirPath()

        # Copy the style sheets and images
        self.styleDir.copyfiles(outputDir)
        (outputDir/'nav.css').remove() # But not nav.css

        # TODO these two should be part of the style
        self.imagesDir.copylist(('panel-amusements.png', 'stock-stop.png'), 
                                outputDir)

        # copy the package's resource files
        package.resourceDir.copyfiles(outputDir)
            
        # Export the package content
        self.pages = [ IMSPage("index", 1, package.root) ]

        self.generatePages(package.root, 2)
        uniquifyNames(self.pages)

        for page in self.pages:
            page.save(outputDir)

        # Create the manifest file
        manifest = Manifest(self.config, outputDir, package, self.pages)
        manifest.save()
        
        # Copy the scripts
        if (os.path.isfile(self.scriptsDir+ "/quizForIMS.js") and 
            os.path.isfile(self.scriptsDir+ "/quizForWeb.js")):
            self.scriptsDir.copylist(('libot_drag.js',
                                      'common.js',
                                      'quizForWeb.js', 
                                      'quizForIMS.js',
                                      'imscp_v1p1.xsd',
                                      'imsmd_v1p2p2.xsd',
                                      'ims_xml.xsd'), outputDir)
            os.remove(self.scriptsDir+ "/quizForWeb.js")
            os.remove(self.scriptsDir+ "/quizForIMS.js")
        else:
            self.scriptsDir.copylist(('libot_drag.js',
                                      'imscp_v1p1.xsd',
                                      'imsmd_v1p2p2.xsd',
                                      'ims_xml.xsd',
                                      'common.js'), outputDir)



        # Zip up the package
        zipped = ZipFile(self.filename, "w")
        for scormFile in outputDir.files():
            zipped.write(scormFile,
                         scormFile.basename().encode('utf8'),
                         ZIP_DEFLATED)
        zipped.close()

        # Clean up the temporary dir
        outputDir.rmtree()
                

    def generatePages(self, node, depth):
        """
        Recursive function for exporting a node.
        'outputDir' is the temporary directory that we are exporting to
        before creating zip file
        """
        for child in node.children:
            pageName = child.title.lower().replace(" ", "_")
            pageName = re.sub(r"\W", "", pageName)
            if not pageName:
                pageName = "__"

            page = IMSPage(pageName, depth, child)

            self.pages.append(page)
            self.generatePages(child, depth + 1)
    
# ===========================================================================