# ===========================================================================
# eXe 
# Copyright 2004-2005, University of Auckland
# Copyright 2004-2007 eXe Project, New Zealand Tertiary Education Commission
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
import re
from cgi                           import escape
from zipfile                       import ZipFile, ZIP_DEFLATED
from exe.webui                     import common
from exe.webui.blockfactory        import g_blockFactory
from exe.engine.error              import Error
from exe.engine.path               import Path, TempDirPath
from exe.export.pages              import Page, uniquifyNames
from exe.engine.uniqueidgenerator  import UniqueIdGenerator

log = logging.getLogger(__name__)


# ===========================================================================
class Manifest(object):
    """
    Represents an imsmanifest xml file
    """
    def __init__(self, config, outputDir, package, pages, scormType):
        """
        Initialize
        'outputDir' is the directory that we read the html from and also output
        the mainfest.xml 
        """
        self.config       = config
        self.outputDir    = outputDir
        self.package      = package
        self.idGenerator  = UniqueIdGenerator(package.name, config.exePath)
        self.pages        = pages
        self.itemStr      = ""
        self.resStr       = ""
        self.scormType    = scormType


    def save(self, filename):
        """
        Save a imsmanifest file to self.outputDir
        """
        out = open(self.outputDir/filename, "w")
        if filename == "imsmanifest.xml":
            out.write(self.createXML().encode('utf8'))
        if filename == "discussionforum.xml":
            out.write(self.createForumXML().encode('utf8'))
        out.close()
        # if user did not supply metadata title, description or creator
        #  then use package title, description, or creator in imslrm
        #  if they did not supply a package title, use the package name
        lrm = self.package.dublinCore.__dict__.copy()
        if lrm.get('title', '') == '':
            lrm['title'] = self.package.title
        if lrm['title'] == '':
            lrm['title'] = self.package.name
        if lrm.get('description', '') == '':
            lrm['description'] = self.package.description
        if lrm['description'] == '':
            lrm['description'] = self.package.name
        if lrm.get('creator', '') == '':
            lrm['creator'] = self.package.author
        # Metadata
        templateFilename = self.config.xulDir/'templates'/'dublincore.xml'
        template = open(templateFilename, 'rb').read()
        xml = template % lrm
        out = open(self.outputDir/'dublincore.xml', 'wb')
        out.write(xml.encode('utf8'))
        out.close()
        # if they don't look like VCARD entries, coerce to fn:
        for f in ('creator', 'publisher', 'contributors'):
            if re.match('.*[:;]', lrm[f]) == None:
                lrm[f] = u'FN:' + lrm[f]
        templateFilename = self.config.xulDir/'templates'/'imslrm.xml'
        template = open(templateFilename, 'rb').read()
        xml = template % lrm
        out = open(self.outputDir/'imslrm.xml', 'wb')
        out.write(xml.encode('utf8'))
        out.close()
        
    def createForumXML(self):
        """
        returning forum XLM string for manifest file
        """  
        xmlStr  = "<?xml version = \"1.0\"?>\n"
        xmlStr += "<forums>\n"
        
        for page in self.pages:
            for idevice in page.node.idevices:
               # if idevice.title == "Discussion Activity":
               if hasattr(idevice, "isForum"):
                    forums = idevice.forumsCache.getForums()
                    xmlStr += self.moodleForums(forums)
                    break
                    
        xmlStr += "</forums>\n"
        
        return xmlStr
    
    def moodleForums(self, forums):
        """
        returning moodle forum XLM string for manifest file
        """ 
        forumStr      = ""
        discussionStr = ""
        for forum in forums:
            if forum.lms.lms == "moodle":
                forumStr += u"<forum><name>%s</name>" % forum.forumName
                forumStr += u"<id>%s</id>" % escape(forum.forumName)
                introduction = forum.introduction
                forumStr += u"<introduction>%s</introduction>" % \
                escape(introduction).replace( '<','&lt;' ).replace( '>', '&gt;' )
                forumStr += u"<type>%s</type>" % forum.lms.type.encode()
                forumStr += u"<studentpost>%s</studentpost>\n" % \
                            forum.lms.studentpost
                forumStr += u"<subscription>%s</subscription>\n" % \
                            forum.lms.subscription
                forumStr += u"<tracking>1</tracking>\n"
                forumStr += u"<attachmentsize></attachmentsize>\n"
                forumStr += u"<ratings>0</ratings>\n"
                forumStr += u"<groupmode>%s</groupmode>\n" % forum.lms.groupmode
                forumStr += u"<visible>%s</visible>\n" % forum.lms.visible
                forumStr += u"</forum>"
                
                for discussion in forum.discussions:
                    discussionStr += u"<discussion>"
                    discussionStr += u"<discussionId>%s</discussionId>" % \
                                     escape(forum.forumName)
                    discussionStr += u"<subject>%s</subject>" \
                                  % escape(discussion.topic)
                    discussionStr += u"<message>%s</message>" \
                    % escape(discussion.intro).replace('<',
                                                    '&lt;').replace('>','&gt;')
                    discussionStr += u"<subscription>send me</subscription>\n"
                    discussionStr += u"</discussion>"
                    
        xml = forumStr + discussionStr
        return xml
    
    def createXML(self):
        """
        returning XLM string for manifest file
        """
        manifestId = unicode(self.idGenerator.generate())
        orgId      = unicode(self.idGenerator.generate())
       
        # Add the namespaces 
        
        if self.scormType == "scorm1.2":
            xmlStr  = u'<?xml version="1.0" encoding="UTF-8"?>\n'
            xmlStr += u'<!-- generated by eXe - http://exelearning.org -->\n'
            xmlStr += u'<manifest identifier="'+manifestId+'" '
            xmlStr += u'xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2" '
            xmlStr += u'xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2" '
            xmlStr += u'xmlns:imsmd="http://www.imsglobal.org/xsd/imsmd_v1p2" '
            xmlStr += u'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            xmlStr += u"xsi:schemaLocation=\"http://www.imsproject.org/xsd/"
            xmlStr += u"imscp_rootv1p1p2 imscp_rootv1p1p2.xsd "        
            xmlStr += u"http://www.imsglobal.org/xsd/imsmd_rootv1p2p1 "
            xmlStr += u"imsmd_rootv1p2p1.xsd "
            xmlStr += u"http://www.adlnet.org/xsd/adlcp_rootv1p2 "
            xmlStr += u"adlcp_rootv1p2.xsd\" "
            xmlStr += u"> \n"
            xmlStr += u"<metadata> \n"
            xmlStr += u" <schema>ADL SCORM</schema> \n"
            xmlStr += u" <schemaversion>1.2</schemaversion> \n"
            xmlStr += u" <adlcp:location>imslrm.xml"
            xmlStr += u"</adlcp:location> \n"
            xmlStr += u"</metadata> \n"
        else:
            xmlStr  = u'<?xml version="1.0" encoding="UTF-8"?>\n'
            xmlStr += u'<!-- generated by eXe - http://exelearning.org -->\n'
            xmlStr += u'<manifest identifier="'+manifestId+'" '
            xmlStr += u'xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2" '
            xmlStr += u'xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2" '
            xmlStr += u'xmlns:imsmd="http://www.imsglobal.org/xsd/imsmd_v1p2" '
            xmlStr += u'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            xmlStr += u"xsi:schemaLocation=\"http://www.imsproject.org/xsd/"
            xmlStr += u"imscp_rootv1p1p2 imscp_rootv1p1p2.xsd "        
            xmlStr += u"http://www.imsglobal.org/xsd/imsmd_rootv1p2p1 "
            xmlStr += u"imsmd_rootv1p2p1.xsd "
            xmlStr += u"http://www.adlnet.org/xsd/adlcp_rootv1p2 "
            xmlStr += u"adlcp_rootv1p2.xsd\" "
            xmlStr += u"> \n"
            
        # Metadata

        xmlStr += u"<organizations default=\""+orgId+"\">  \n"
        xmlStr += u"<organization identifier=\""+orgId
        xmlStr += u"\" structure=\"hierarchical\">  \n"

        if self.package.title != '':
            title = escape(self.package.title)
        else:
            title  = escape(self.package.root.titleShort)
        xmlStr += u"<title>"+title+"</title>\n"
        
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
        Returning xlm string for items and resources
        """
        itemId   = "ITEM-"+unicode(self.idGenerator.generate())
        resId    = "RES-"+unicode(self.idGenerator.generate())
        filename = page.name+".html"
            
        
        self.itemStr += "<item identifier=\""+itemId+"\" isvisible=\"true\" "
        self.itemStr += "identifierref=\""+resId+"\">\n"
        self.itemStr += "    <title>"
        self.itemStr += escape(page.node.titleShort)
        self.itemStr += "</title>\n"
        
        self.resStr += "<resource identifier=\""+resId+"\" "
        self.resStr += "type=\"webcontent\" "

        # Add the scorm type
        self.resStr += "adlcp:scormtype=\"sco\" "

        self.resStr += "href=\""+filename+"\"> \n"
        self.resStr += """\
    <file href="%s"/>
    <file href="base.css"/>
    <file href="content.css"/>
    <file href="APIWrapper.js"/>
    <file href="SCOFunctions.js"/>""" %filename
        self.resStr += "\n"
        fileStr = ""

        for resource in page.node.getResources():            
            fileStr += "    <file href=\""+escape(resource)+"\"/>\n"

        self.resStr += fileStr
        self.resStr += "</resource>\n"


# ===========================================================================
class ScormPage(Page):
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
        out.write(self.render())
        out.close()


    def render(self):
        """
        Returns an XHTML string rendering this page.
        """
        html  = common.docType()
        html += u"<html xmlns=\"http://www.w3.org/1999/xhtml\">\n"
        html += u"<head>\n"
        html += u"<title>"+_("eXe")+"</title>\n"
        html += u"<meta http-equiv=\"Content-Type\" content=\"text/html; "
        html += u" charset=utf-8\" />\n";
        html += u"<style type=\"text/css\">\n"
        html += u"@import url(base.css);\n"
        html += u"@import url(content.css);\n"
        html += u"</style>\n"
        html += u"<script type=\"text/javascript\" "
        html += u"src=\"APIWrapper.js\"></script>\n" 
        html += u"<script type=\"text/javascript\" "
        html += u"src=\"SCOFunctions.js\"></script>\n"             
        html += u'<script type="text/javascript" src="common.js"></script>\n'
        html += u"</head>\n"
        html += u'<body onload="loadPage()" ' #  onbeforeunload="unloadPage()" '
        html += u'onunload="unloadPage()">'
        html += u"<div id=\"outer\">\n"
        html += u"<div id=\"main\">\n"
        html += u"<div id=\"nodeDecoration\">\n"
        html += u"<p id=\"nodeTitle\">\n"
        html += escape(self.node.titleLong)
        html += u'</p></div>\n'

        for idevice in self.node.idevices:
            block = g_blockFactory.createBlock(None, idevice)
            if not block:
                log.critical("Unable to render iDevice.")
                raise Error("Unable to render iDevice.")
            if hasattr(idevice, "isQuiz"):
                html += block.renderJavascriptForScorm()
            html += block.renderView(self.node.package.style)

        html += u"</div>\n"
        html += u"</div>\n"
        if self.node.package.scolinks:
            html += u'<a class="previouslink" '
            html += u'href="javascript: goBack();">%s</a> | <a class="nextlink" ' % _('Previous')
            html += u'href="javascript: goForward();">%s</a>' % _('Next')
        html += self.renderLicense()
        html += self.renderFooter()
        html += u"</body></html>\n"
        html = html.encode('utf8')
        return html


# ===========================================================================
class ScormExport(object):
    """
    Exports an eXe package as a SCORM package
    """
    def __init__(self, config, styleDir, filename, scormType):
        """ 
        Initialize
        'styleDir' is the directory from which we will copy our style sheets
        (and some gifs)
        """
        self.config       = config
        self.imagesDir    = config.webDir/"images"
        self.scriptsDir   = config.webDir/"scripts"
        self.templatesDir = config.webDir/"templates"
        self.schemasDir   = config.webDir/"schemas"
        self.styleDir     = Path(styleDir)
        self.filename     = Path(filename)
        self.pages        = []
        self.hasForum     = False
        self.scormType    = scormType


    def export(self, package):
        """ 
        Export SCORM package
        """
        # First do the export to a temporary directory
        outputDir = TempDirPath()

        # Copy the style sheet files to the output dir
        # But not nav.css
        styleFiles  = [self.styleDir/'..'/'base.css']
        styleFiles += [self.styleDir/'..'/'popup_bg.gif']
        styleFiles += self.styleDir.files("*.css")
        if "nav.css" in styleFiles:
            styleFiles.remove("nav.css")
        styleFiles += self.styleDir.files("*.jpg")
        styleFiles += self.styleDir.files("*.gif")
        styleFiles += self.styleDir.files("*.png")
        styleFiles += self.styleDir.files("*.js")
        styleFiles += self.styleDir.files("*.html")
        self.styleDir.copylist(styleFiles, outputDir)

        # copy the package's resource files
        package.resourceDir.copyfiles(outputDir)
      
            
        # Export the package content
        self.pages = [ ScormPage("index", 1, package.root) ]

        self.generatePages(package.root, 2)
        uniquifyNames(self.pages)

        for page in self.pages:
            page.save(outputDir)
            if not self.hasForum:
                for idevice in page.node.idevices:
                    if hasattr(idevice, "isForum"):
                        if idevice.forum.lms.lms == "moodle":
                            self.hasForum = True
                            break

        # Create the manifest file
        manifest = Manifest(self.config, outputDir, package, self.pages, self.scormType)
        manifest.save("imsmanifest.xml")
        if self.hasForum:
            manifest.save("discussionforum.xml")
        
        # Copy the scripts
        self.scriptsDir.copylist(('APIWrapper.js', 
                                  'SCOFunctions.js', 
                                  'libot_drag.js',
                                  'common.js'), outputDir)
        schemasDir = ""
        if self.scormType == "scorm1.2":
            schemasDir = self.schemasDir/"scorm1.2"
        else:
            schemasDir = self.schemasDir/"scorm2004"

        schemasDir.copylist(('imscp_rootv1p1p2.xsd',
                            'imsmd_rootv1p2p1.xsd',
                            'adlcp_rootv1p2.xsd',
                            'ims_xml.xsd'), outputDir)
 

        # copy players for media idevices.                
        hasFlowplayer     = False
        hasMagnifier      = False
        hasXspfplayer     = False
        isBreak           = False
        
        for page in self.pages:
            if isBreak:
                break
            for idevice in page.node.idevices:
                if (hasFlowplayer and hasMagnifier and hasXspfplayer):
                    isBreak = True
                    break
                if not hasFlowplayer:
                    if 'flowPlayer.swf' in idevice.systemResources:
                        hasFlowplayer = True
                if not hasMagnifier:
                    if 'magnifier.swf' in idevice.systemResources:
                        hasMagnifier = True
                if not hasXspfplayer:
                    if 'xspf_player.swf' in idevice.systemResources:
                        hasXspfplayer = True
                        
        if hasFlowplayer:
            videofile = (self.templatesDir/'flowPlayer.swf')
            videofile.copyfile(outputDir/'flowPlayer.swf')
        if hasMagnifier:
            videofile = (self.templatesDir/'magnifier.swf')
            videofile.copyfile(outputDir/'magnifier.swf')
        if hasXspfplayer:
            videofile = (self.templatesDir/'xspf_player.swf')
            videofile.copyfile(outputDir/'xspf_player.swf')

        # Copy a copy of the GNU Free Documentation Licence
        (self.templatesDir/'fdl.html').copyfile(outputDir/'fdl.html')
        # Zip it up!
        self.filename.safeSave(self.doZip, _('EXPORT FAILED!\nLast succesful export is %s.'), outputDir)
        # Clean up the temporary dir
        outputDir.rmtree()

    def doZip(self, fileObj, outputDir):
        """
        Actually does the zipping of the file. Called by 'Path.safeSave'
        """
        # Zip up the scorm package
        zipped = ZipFile(fileObj, "w")
        for scormFile in outputDir.files():
            zipped.write(scormFile,
                         scormFile.basename().encode('utf8'),
                         ZIP_DEFLATED)
        zipped.close()

    def generatePages(self, node, depth):
        """
        Recursive function for exporting a node.
        'node' is the node that we are making a page for
        'depth' is the number of ancestors that the page has +1 (ie. root is 1)
        """
        for child in node.children:
            pageName = child.titleShort.lower().replace(" ", "_")
            pageName = re.sub(r"\W", "", pageName)
            if not pageName:
                pageName = "__"

            page = ScormPage(pageName, depth, child)

            self.pages.append(page)
            self.generatePages(child, depth + 1)
    
# ===========================================================================
