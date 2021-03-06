/* Based on Moxiecode's $Id: editor_plugin_src.js 201 2007-02-12 15:56:56Z spocke $ */

/* Import plugin specific language pack */ 
tinyMCE.importPluginLanguagePack('pastecode');

var TinyMCE_PasteCodePlugin = {
	getInfo : function() {
		return {
			longname : 'Paste code',
			version : tinyMCE.majorVersion + "." + tinyMCE.minorVersion
		};
	},

	initInstance : function(inst) {
		if (tinyMCE.isMSIE)
			tinyMCE.addEvent(inst.getBody(), "pastecode", TinyMCE_PasteCodePlugin._handlePasteEvent);
	},

	handleEvent : function() {
		return true;
	},

	getControlHTML : function(cn) { 
		switch (cn) { 
			case "pastecode":
				return tinyMCE.getButtonHTML(cn, 'lang_paste_code_desc', '{$pluginurl}/images/pastecode.gif', 'mcePasteCode', true);
			case "pastehtml":
				return tinyMCE.getButtonHTML(cn, 'lang_paste_html_desc', '{$pluginurl}/images/pastehtml.gif', 'mcePasteHtml', true);		
		}
		return ''; 
	},

	execCommand : function(editor_id, element, command, user_interface, value) { 
		switch (command) { 
			case "mcePasteCode": 
				if (user_interface) {
					if ((tinyMCE.isMSIE && !tinyMCE.isOpera) && !tinyMCE.getParam('paste_use_dialog', false))
						TinyMCE_PasteCodePlugin._insertCode(clipboardData.getData("Text"), true); 
					else { 
						var template = new Array(); 
						template['file']	= '../../plugins/pastecode/pastecode.htm'; // Relative to theme 
						template['width']  = 450; 
						template['height'] = 400; 
						var plain_text = ""; 
						tinyMCE.openWindow(template, {editor_id : editor_id, plain_text: plain_text, resizable : "yes", scrollbars : "no", inline : "yes", mceDo : 'insert'}); 
					}
				} else
					TinyMCE_PasteCodePlugin._insertCode(value['html'],value['wrapper']);

				return true;

			case "mcePasteHtml": 
				if (user_interface) {
					if ((tinyMCE.isMSIE && !tinyMCE.isOpera) && !tinyMCE.getParam('paste_use_dialog', false))
						TinyMCE_PasteCodePlugin._insertHTML(clipboardData.getData("Text"), true); 
					else { 
						var template = new Array(); 
						template['file']	= '../../plugins/pastecode/pastehtml.htm'; // Relative to theme 
						template['width']  = 450; 
						template['height'] = 400; 
						var plain_text = ""; 
						tinyMCE.openWindow(template, {editor_id : editor_id, plain_text: plain_text, resizable : "yes", scrollbars : "no", inline : "yes", mceDo : 'insert'}); 
					}
				} else
					TinyMCE_PasteCodePlugin._insertHTML(value['html']);

				return true;
		} 

		// Pass to next handler in chain 
		return false; 
	},

	// Private plugin internal methods

	_handlePasteEvent : function(e) {
		switch (e.type) {
			case "pastecode":
				var html = TinyMCE_PasteCodePlugin._clipboardHTML();
				var r, inst = tinyMCE.selectedInstance;

				// Removes italic, strong etc, the if was needed due to bug #1437114
				if (inst && (r = inst.getRng()) && r.text.length > 0)
					tinyMCE.execCommand('delete');

				if (html && html.length > 0)
					tinyMCE.execCommand('mcePasteCode', false, html);

				tinyMCE.cancelEvent(e);
				return false;

			case "pastehtml":
				var html = TinyMCE_PasteCodePlugin._clipboardHTML();
				var r, inst = tinyMCE.selectedInstance;

				// Removes italic, strong etc, the if was needed due to bug #1437114
				if (inst && (r = inst.getRng()) && r.text.length > 0)
					tinyMCE.execCommand('delete');

				if (html && html.length > 0)
					tinyMCE.execCommand('mcePasteHtml', false, html);

				tinyMCE.cancelEvent(e);
				return false;
		}

		return true;
	},

	_insertCode : function(content,wrapper) { 
		if (content && content.length > 0) {
			var c = "<pre><code>"+content.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')+"</code></pre>";
			if (wrapper) c = "<div class='pre-code'>"+c+"</div>";
			tinyMCE.execCommand("mceInsertRawHTML", false, c); 
		}
	},

	_insertHTML : function(content) { 
		if (content && content.length > 0) {
			tinyMCE.execCommand("mceInsertRawHTML", false, content);
		}
	},

	_clipboardHTML : function() {
		var div = document.getElementById('_TinyMCE_clipboardHTML');

		if (!div) {
			var div = document.createElement('DIV');
			div.id = '_TinyMCE_clipboardHTML';

			with (div.style) {
				visibility = 'hidden';
				overflow = 'hidden';
				position = 'absolute';
				width = 1;
				height = 1;
			}

			document.body.appendChild(div);
		}

		div.innerHTML = '';
		var rng = document.body.createTextRange();
		rng.moveToElementText(div);
		rng.execCommand('Paste');
		var html = div.innerHTML;
		div.innerHTML = '';
		return html;
	}
};

tinyMCE.addPlugin("pastecode", TinyMCE_PasteCodePlugin);
