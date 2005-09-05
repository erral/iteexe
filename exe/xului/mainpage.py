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
This is the main XUL page.
"""

import os
import sys
import logging
from twisted.web                 import static
from nevow                       import loaders, inevow, stan
from nevow.livepage              import handler, js
from exe.webui.renderable        import RenderableLivePage
from exe.webui.idevicepane       import IdevicePane
from exe.webui.authoringpage     import AuthoringPage
from exe.webui.outlinepane       import OutlinePane
from exe.webui.stylemenu         import StyleMenu
from exe.webui.propertiespage    import PropertiesPage
from exe.export.websiteexport    import WebsiteExport
from exe.export.singlepageexport import SinglePageExport
from exe.export.scormexport      import ScormExport
from exe.export.imsexport        import IMSExport
from exe.engine.path             import Path

log = logging.getLogger(__name__)


class MainPage(RenderableLivePage):
    """
    This is the main XUL page.  Responsible for handling URLs.
    Rendering and processing is delegated to the Pane classes.
    """
    
    _templateFileName = 'mainpage.xul'
    name = 'to_be_defined'

    def __init__(self, parent, package):
        """
        Initialize a new XUL page
        'package' is the package that we look after
        """
        self.name = package.name
        RenderableLivePage.__init__(self, parent, package)
        self.putChild("resources", static.File(package.resourceDir))

        mainxul = Path(self.config.webDir).joinpath('templates', 'mainpage.xul')
        self.docFactory  = loaders.xmlfile(mainxul)

        # Create all the children on the left
        self.outlinePane = OutlinePane(self)
        self.idevicePane = IdevicePane(self)
        self.styleMenu   = StyleMenu(self)

        # And in the main section
        self.authoringPage  = AuthoringPage(self)
        self.propertiesPage = PropertiesPage(self)
        self.error = False


    def getChild(self, name, request):
        """
        Try and find the child for the name given
        """
        if name == '':
            return self
        else:
            return super(self, self.__class__).getChild(self, name, request)


    def goingLive(self, ctx, client):
        """Called each time the page is served/refreshed"""
        inevow.IRequest(ctx).setHeader('content-type',
                                       'application/vnd.mozilla.xul+xml')
        # Set up named server side funcs that js can call
        def setUpHandler(func, name, *args, **kwargs):
            """
            Convience function link funcs to hander ids
            and store them
            """
            kwargs['identifier'] = name
            hndlr = handler(func, *args, **kwargs)
            hndlr(ctx, client) # Stores it
        setUpHandler(self.handleIsPackageDirty, 'isPackageDirty')
        setUpHandler(self.handlePackageFileName, 'getPackageFileName')
        setUpHandler(self.handleSavePackage, 'savePackage')
        setUpHandler(self.handleLoadPackage, 'loadPackage')
        setUpHandler(self.handleLoadTutorialPackage, 'loadTutorialPackage')
        setUpHandler(self.handleExport, 'exportPackage')
        self.idevicePane.client = client


    def render_addChild(self, ctx, data):
        """Fills in the oncommand handler for the 
        add child button and short cut key"""
        return ctx.tag(oncommand=handler(self.outlinePane.handleAddChild,
                       js('currentOutlineId()')))


    def render_delNode(self, ctx, data):
        """Fills in the oncommand handler for the 
        delete child button and short cut key"""
        return ctx.tag(oncommand=handler(self.outlinePane.handleDelNode,
                       js("confirmDelete()"),
                       js('currentOutlineId()')))


    def render_renNode(self, ctx, data):
        """Fills in the oncommand handler for the 
        rename node button and short cut key"""
        return ctx.tag(oncommand=handler(self.outlinePane.handleRenNode,
                       js('currentOutlineId()'),
                       js('askNodeName()'), bubble=True))


    def render_prePath(self, ctx, data):
        """Fills in the package name to certain urls in the xul"""
        request = inevow.IRequest(ctx)
        return ctx.tag(src=self.package.name + '/' + ctx.tag.attributes['src'])


    # The node moving buttons
    def _passHandle(self, ctx, name):
        """Ties up a handler for the promote, demote,
        up and down buttons. (Called by below funcs)"""
        attr = getattr(self.outlinePane, 'handle%s' % name)
        return ctx.tag(oncommand=handler(attr, js('currentOutlineId()')))


    def render_promote(self, ctx, data):
        """Fills in the oncommand handler for the 
        Promote button and shortcut key"""
        return self._passHandle(ctx, 'Promote')


    def render_demote(self, ctx, data):
        """Fills in the oncommand handler for the 
        Demote button and shortcut key"""
        return self._passHandle(ctx, 'Demote')


    def render_up(self, ctx, data):
        """Fills in the oncommand handler for the 
        Up button and shortcut key"""
        return self._passHandle(ctx, 'Up')


    def render_down(self, ctx, data):
        """Fills in the oncommand handler for the 
        Down button and shortcut key"""
        return self._passHandle(ctx, 'Down')


    def render_debugInfo(self, ctx, data):
        """Renders debug info to the top
        of the screen if logging is set to debug level
        """
        if log.getEffectiveLevel() == logging.DEBUG:
            # TODO: Needs to be updated by xmlhttp or xmlrpc
            request = inevow.IRequest(ctx)
            return stan.xml(('<hbox id="header">\n'
                             '    <label>%s</label>\n'
                             '    <label>%s</label>\n'
                             '</hbox>\n' %
                             (request.prepath, self.package.name)))
        else:
            return ''


    def handleIsPackageDirty(self, client, ifClean, ifDirty):
        """
        Called by js to know if the package is dirty or not.
        ifClean is JavaScript to be evaled on the client if the package has
        been changed 
        ifDirty is JavaScript to be evaled on the client if the package has not
        been changed
        """
        if self.package.isChanged:
            client.sendScript(ifDirty)
        else:
            client.sendScript(ifClean)


    def handlePackageFileName(self, client, onDone, onDoneParam):
        """
        Calls the javascript func named by 'onDone' passing as the
        only parameter the filename of our package. If the package
        has never been saved or loaded, it passes an empty string
        'onDoneParam' will be passed to onDone as a param after the
        filename
        """
        client.call(onDone, unicode(self.package.filename), onDoneParam)


    def handleSavePackage(self, client, filename=None, onDone=None):
        """Save the current package
        'filename' is the filename to save the package to
        'onDone' will be evaled after saving instead or redirecting
        to the new location (in cases of package name changes).
        (This is used where the user goes file|open when their 
        package is changed and needs saving)
        """
        oldName = self.package.name
        # If the script is not passing a filename to us,
        # Then use the last filename that the package was loaded from/saved to
        if filename:
            encoding = sys.getfilesystemencoding()
            if encoding is None:
                encoding = 'ascii'
            filename = unicode(filename, encoding)
        else:
            filename = self.package.filename
            assert (filename, 
                    ('Somehow save was called without a filename '
                     'on a package that has no default filename.'))
        # Add the extension if its not already there
        if not filename.lower().endswith('.elp'):
            filename += '.elp'
        self.package.save(filename) # This can change the package name
        client.alert(_(u'Package saved to: %s' % filename))
        if onDone:
            client.sendScript(onDone)
        elif self.package.name != oldName:
            # Redirect the client if the package name has changed
            self.webserver.root.putChild(self.package.name, self)
            log.info('Package saved, redirecting client to /%s'
                     % self.package.name)
            client.sendScript('top.location = "/%s"' % \
                              self.package.name.encode('utf8'))


    def handleLoadPackage(self, client, filename):
        """Load the package named 'filename'"""
        try:
            encoding = sys.getfilesystemencoding()
            if encoding is None:
                encoding = 'ascii'
            filename = unicode(filename, encoding)
            log.debug("filename and path" + filename)
            packageStore = self.webserver.application.packageStore
            package = packageStore.loadPackage(filename)
            self.root.bindNewPackage(package)
            client.sendScript((u'top.location = "/%s"' % \
                              package.name).encode('utf8'))
        except Exception, exc:
            if log.getEffectiveLevel() == logging.DEBUG:
                client.alert(_(u'Sorry, wrong file format:\n%s') % unicode(exc))
            else:
                client.alert(_(u'Sorry, wrong file format'))
            log.error(_(u'Error loading package "%s": %s') % \
                      (filename, unicode(exc)))
            self.error = True


    def handleLoadTutorialPackage(self, client):
        """Load the tutorial"""
        try:
            filename = self.config.webDir/"eXe-tutorial.elp"
            packageStore = self.webserver.application.packageStore
            package = packageStore.loadPackage(filename)
            self.root.bindNewPackage(package)
            client.sendScript((u'top.location = "/%s"' % \
                              package.name).encode('utf8'))
        except Exception, exc:
            if log.getEffectiveLevel() == logging.DEBUG:
                client.alert(_(u'Sorry, wrong file format:\n%s') % unicode(exc))
            else:
                client.alert(_(u'Sorry, wrong file format'))
            log.error(_(u'Error loading package "%s": %s' % \
                      (filename, unicode(exc))))
            self.error = True


    def handleExport(self, client, exportType, filename):
        """
        Called by js. 
        'exportType' can be one of 'scormMeta' 'scormNoMeta' 'scormNoScormType'
        'webSite'
        Exports the current package to one of the above formats
        'filename' is a file for scorm pages, and a directory for websites
        """
        webDir     = Path(self.config.webDir)
        stylesDir  = webDir.joinpath('style', self.package.style)

        if exportType == 'singlePage':
            self.exportSinglePage(client, filename, webDir, stylesDir)

        elif exportType == 'webSite':
            self.exportWebSite(client, filename, webDir, stylesDir)

        elif exportType == "scorm":
            self.exportScorm(client, filename, stylesDir)

        else:
            self.exportIMS(client, filename, stylesDir)


    def exportSinglePage(self, client, filename, webDir, stylesDir):
        """
        Export 'client' to a single web page,
        'webDir' is just read from config.webDir
        'stylesDir' is where to copy the style sheet information from
        """
        imagesDir  = webDir.joinpath('images')
        scriptsDir = webDir.joinpath('scripts')
        # filename is a directory where we will export the website to
        # We assume that the user knows what they are doing
        # and don't check if the directory is already full or not
        # and we just overwrite what's already there
        filename = Path(filename)
        # Append the package name to the folder path if necessary
        if filename.basename() != self.package.name:
            filename /= self.package.name
        if not filename.exists():
            filename.makedirs()
        elif not filename.isdir():
            client.alert(_(u'Filename %s is a file, cannot replace it') % 
                         filename)
            log.error("Couldn't export web page: "+
                      "Filename %s is a file, cannot replace it" % filename)
            return
        else:
            # Wipe it out
            filename.rmtree()
            filename.mkdir()
        # Now do the export
        singlePageExport = SinglePageExport(stylesDir, filename, 
                                            imagesDir, scriptsDir)
        singlePageExport.export(self.package)
        # Show the newly exported web site in a new window
        if hasattr(os, 'startfile'):
            os.startfile(filename)
        else:
            filename /= 'index.html'
            os.spawnvp(os.P_NOWAIT, self.config.browserPath, 
                (self.config.browserPath,
                 '-remote', 'openURL(%s, new-window)' % \
                 filename))


    def exportWebSite(self, client, filename, webDir, stylesDir):
        """
        Export 'client' to a web site,
        'webDir' is just read from config.webDir
        'stylesDir' is where to copy the style sheet information from
        """
        imagesDir  = webDir.joinpath('images')
        scriptsDir = webDir.joinpath('scripts')
        # filename is a directory where we will export the website to
        # We assume that the user knows what they are doing
        # and don't check if the directory is already full or not
        # and we just overwrite what's already there
        filename = Path(filename)
        # Append the package name to the folder path if necessary
        if filename.basename() != self.package.name:
            filename /= self.package.name
        if not filename.exists():
            filename.makedirs()
        elif not filename.isdir():
            client.alert(_(u'Filename %s is a file, cannot replace it') % 
                         filename)
            log.error("Couldn't export web page: "+
                      "Filename %s is a file, cannot replace it" % filename)
            return
        else:
            # Wipe it out
            filename.rmtree()
            filename.mkdir()
        # Now do the export
        websiteExport = WebsiteExport(stylesDir, filename, 
                                      imagesDir, scriptsDir)
        websiteExport.export(self.package)
        # Show the newly exported web site in a new window
        if hasattr(os, 'startfile'):
            os.startfile(filename)
        else:
            filename /= 'index.html'
            os.spawnvp(os.P_NOWAIT, self.config.browserPath, 
                (self.config.browserPath,
                 '-remote', 'openURL(%s, new-window)' % \
                 filename))


    def exportScorm(self, client, filename, stylesDir):
        """
        Exports this package to a scorm package file
        """
        log.debug(u"exportScorm, filaneme=%s" % filename)
        # Append an extension if required
        filename = unicode(filename, 'utf8')
        if not filename.lower().endswith('.zip'): 
            filename += '.zip'
        filename = Path(filename)
        # Remove any old existing files
        if filename.exists(): 
            filename.remove()
        # Do the export
        scormExport = ScormExport(self.config, stylesDir, filename)
        scormExport.export(self.package)
        client.alert(_(u'Exported to %s') % filename)


    def exportIMS(self, client, filename, stylesDir):
        """
        Exports this package to a ims package file
        """
        log.debug(u"exportIMS")
        # Append an extension if required
        if not filename.lower().endswith('.zip'): 
            filename += '.zip'
        filename = Path(filename)
        # Remove any old existing files
        if filename.exists(): 
            filename.remove()
        # Do the export
        imsExport = IMSExport(self.config, stylesDir, filename)
        imsExport.export(self.package)
        client.alert(_(u'Exported to %s' % filename))