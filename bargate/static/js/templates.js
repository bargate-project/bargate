(function() {(window.nunjucksPrecompiled = window.nunjucksPrecompiled || {})["breadcrumbs.html"] = (function() {
function root(env, context, frame, runtime, cb) {
var lineno = null;
var colno = null;
var output = "";
try {
var parentTemplate = null;
output += "<ol class=\"breadcrumb\">\n\t\t<li>\n\t\t\t<i class=\"fa fa-home\"></i>\n\t\t\t<a class=\"edir\" data-url=\"";
output += runtime.suppressValue(runtime.contextOrFrameLookup(context, frame, "root_url"), env.opts.autoescape);
output += "\">\n\t\t\t";
output += runtime.suppressValue(runtime.contextOrFrameLookup(context, frame, "root_name"), env.opts.autoescape);
output += "\n\t\t\t</a>\n\t\t</li>";
frame = frame.push();
var t_3 = runtime.contextOrFrameLookup(context, frame, "crumbs");
if(t_3) {var t_2 = t_3.length;
for(var t_1=0; t_1 < t_3.length; t_1++) {
var t_4 = t_3[t_1];
frame.set("dir", t_4);
frame.set("loop.index", t_1 + 1);
frame.set("loop.index0", t_1);
frame.set("loop.revindex", t_2 - t_1);
frame.set("loop.revindex0", t_2 - t_1 - 1);
frame.set("loop.first", t_1 === 0);
frame.set("loop.last", t_1 === t_2 - 1);
frame.set("loop.length", t_2);
output += "\n\t\t<li";
if(runtime.memberLookup((runtime.contextOrFrameLookup(context, frame, "loop")),"last")) {
output += " class=\"active\"";
;
}
output += ">";
if(!runtime.memberLookup((runtime.contextOrFrameLookup(context, frame, "loop")),"last")) {
output += "<a class=\"edir\" data-url=\"";
output += runtime.suppressValue(runtime.memberLookup((t_4),"url"), env.opts.autoescape);
output += "\">";
output += runtime.suppressValue(runtime.memberLookup((t_4),"name"), env.opts.autoescape);
output += "</a>";
;
}
else {
output += runtime.suppressValue(runtime.memberLookup((t_4),"name"), env.opts.autoescape);
;
}
output += "\n\t\t</li>";
;
}
}
frame = frame.pop();
output += "\n</ol>\n";
if(parentTemplate) {
parentTemplate.rootRenderFunc(env, context, frame, runtime, cb);
} else {
cb(null, output);
}
;
} catch (e) {
  cb(runtime.handleError(e, lineno, colno));
}
}
return {
root: root
};

})();
})();
(function() {(window.nunjucksPrecompiled = window.nunjucksPrecompiled || {})["directory-grid.html"] = (function() {
function root(env, context, frame, runtime, cb) {
var lineno = null;
var colno = null;
var output = "";
try {
var parentTemplate = null;
output += "<div id=\"dirs\">";
frame = frame.push();
var t_3 = runtime.contextOrFrameLookup(context, frame, "shares");
if(t_3) {var t_2 = t_3.length;
for(var t_1=0; t_1 < t_3.length; t_1++) {
var t_4 = t_3[t_1];
frame.set("entry", t_4);
frame.set("loop.index", t_1 + 1);
frame.set("loop.index0", t_1);
frame.set("loop.revindex", t_2 - t_1);
frame.set("loop.revindex0", t_2 - t_1 - 1);
frame.set("loop.first", t_1 === 0);
frame.set("loop.last", t_1 === t_2 - 1);
frame.set("loop.length", t_2);
output += "<div class=\"grid-entry eshare\" data-url=\"";
output += runtime.suppressValue((lineno = 2, colno = 51, runtime.callWrap(runtime.contextOrFrameLookup(context, frame, "buildurl"), "buildurl", context, [runtime.memberLookup((t_4),"burl"),runtime.memberLookup((t_4),"name"),"browse"])), env.opts.autoescape);
output += "\" data-sortname=\"";
output += runtime.suppressValue(env.getFilter("lower").call(context, runtime.memberLookup((t_4),"name")), env.opts.autoescape);
output += "\">\n\t\t<div class=\"panel panel-default\">\n\t\t\t<div class=\"panel-body grid-icon\"><span class=\"fa fa-fw fa-hdd-o\"></span></div>\n\t\t\t<div class=\"panel-footer\" ";
if(env.getFilter("length").call(context, runtime.memberLookup((t_4),"name")) > 18) {
output += " rel=\"tooltip\" title=\"";
output += runtime.suppressValue(runtime.memberLookup((t_4),"name"), env.opts.autoescape);
output += "\"";
;
}
output += ">";
output += runtime.suppressValue(runtime.memberLookup((t_4),"name"), env.opts.autoescape);
output += "</div>\n\t\t</div>\n\t</div>";
;
}
}
frame = frame.pop();
frame = frame.push();
var t_7 = runtime.contextOrFrameLookup(context, frame, "dirs");
if(t_7) {var t_6 = t_7.length;
for(var t_5=0; t_5 < t_7.length; t_5++) {
var t_8 = t_7[t_5];
frame.set("entry", t_8);
frame.set("loop.index", t_5 + 1);
frame.set("loop.index0", t_5);
frame.set("loop.revindex", t_6 - t_5);
frame.set("loop.revindex0", t_6 - t_5 - 1);
frame.set("loop.first", t_5 === 0);
frame.set("loop.last", t_5 === t_6 - 1);
frame.set("loop.length", t_6);
output += "<div class=\"grid-entry edir\" data-url=\"";
output += runtime.suppressValue((lineno = 10, colno = 49, runtime.callWrap(runtime.contextOrFrameLookup(context, frame, "buildurl"), "buildurl", context, [runtime.memberLookup((t_8),"burl"),runtime.memberLookup((t_8),"path"),"browse"])), env.opts.autoescape);
output += "\" data-filename=\"";
output += runtime.suppressValue(runtime.memberLookup((t_8),"name"), env.opts.autoescape);
output += "\" data-sortname=\"";
output += runtime.suppressValue(env.getFilter("lower").call(context, runtime.memberLookup((t_8),"name")), env.opts.autoescape);
output += "\">\n\t\t<div class=\"panel panel-default\">\n\t\t\t<div class=\"panel-footer\" ";
if(env.getFilter("length").call(context, runtime.memberLookup((t_8),"name")) > 18) {
output += " rel=\"tooltip\" title=\"";
output += runtime.suppressValue(runtime.memberLookup((t_8),"name"), env.opts.autoescape);
output += "\"";
;
}
output += "><i class=\"fa fa-fw fa-folder\"></i> ";
output += runtime.suppressValue(runtime.memberLookup((t_8),"name"), env.opts.autoescape);
output += "</div>\n\t\t</div>\n\t</div>";
;
}
}
frame = frame.pop();
output += "</div>\n\n<div class=\"clearfix\"></div>\n\n<div id=\"files\">";
frame = frame.push();
var t_11 = runtime.contextOrFrameLookup(context, frame, "files");
if(t_11) {var t_10 = t_11.length;
for(var t_9=0; t_9 < t_11.length; t_9++) {
var t_12 = t_11[t_9];
frame.set("entry", t_12);
frame.set("loop.index", t_9 + 1);
frame.set("loop.index0", t_9);
frame.set("loop.revindex", t_10 - t_9);
frame.set("loop.revindex0", t_10 - t_9 - 1);
frame.set("loop.first", t_9 === 0);
frame.set("loop.last", t_9 === t_10 - 1);
frame.set("loop.length", t_10);
output += "<div class=\"grid-entry efile\" data-mtyper=\"";
output += runtime.suppressValue(runtime.memberLookup((t_12),"mtyper"), env.opts.autoescape);
output += "\" data-mtimer=\"";
output += runtime.suppressValue(runtime.memberLookup((t_12),"mtimer"), env.opts.autoescape);
output += "\" data-sizer=\"";
output += runtime.suppressValue(runtime.memberLookup((t_12),"size"), env.opts.autoescape);
output += "\" data-icon=\"fa fa-fw fa-";
output += runtime.suppressValue(runtime.memberLookup((t_12),"icon"), env.opts.autoescape);
output += "\" ";
if(runtime.memberLookup((t_12),"img")) {
output += "data-img=\"true\" ";
;
}
output += " data-mtype=\"";
output += runtime.suppressValue(runtime.memberLookup((t_12),"mtype"), env.opts.autoescape);
output += "\" data-filename=\"";
output += runtime.suppressValue(runtime.memberLookup((t_12),"name"), env.opts.autoescape);
output += "\" data-mtime=\"";
output += runtime.suppressValue(runtime.memberLookup((t_12),"mtime"), env.opts.autoescape);
output += "\" data-size=\"";
output += runtime.suppressValue(env.getFilter("filesizeformat").call(context, runtime.memberLookup((t_12),"size"),runtime.makeKeywordArgs({"binary": runtime.contextOrFrameLookup(context, frame, "True")})), env.opts.autoescape);
output += "\" data-path=\"";
output += runtime.suppressValue(runtime.memberLookup((t_12),"path"), env.opts.autoescape);
output += "\" data-sortname=\"";
output += runtime.suppressValue(env.getFilter("lower").call(context, runtime.memberLookup((t_12),"name")), env.opts.autoescape);
output += "\" data-burl=\"";
output += runtime.suppressValue(runtime.memberLookup((t_12),"burl"), env.opts.autoescape);
output += "\" ";
if(runtime.memberLookup((t_12),"view")) {
output += "data-view=\"true\"";
;
}
output += ">";
if(runtime.memberLookup((t_12),"img")) {
output += "<div class=\"panel panel-default\">\n\t\t\t<div class=\"panel-body grid-img\" style=\"background-image: url('";
output += runtime.suppressValue((lineno = 26, colno = 75, runtime.callWrap(runtime.contextOrFrameLookup(context, frame, "buildurl"), "buildurl", context, [runtime.memberLookup((t_12),"burl"),runtime.memberLookup((t_12),"path"),"preview"])), env.opts.autoescape);
output += "')\"></div>";
;
}
else {
output += "<div class=\"panel panel-default\">\n\t\t\t<div class=\"panel-body grid-icon\"><span class=\"fa fa-fw fa-";
output += runtime.suppressValue(runtime.memberLookup((t_12),"icon"), env.opts.autoescape);
output += "\"></span></div>";
;
}
output += "<div class=\"panel-footer\" ";
if(env.getFilter("length").call(context, runtime.memberLookup((t_12),"name")) > 18) {
output += " rel=\"tooltip\" title=\"";
output += runtime.suppressValue(runtime.memberLookup((t_12),"name"), env.opts.autoescape);
output += "\"";
;
}
output += ">";
output += runtime.suppressValue(runtime.memberLookup((t_12),"name"), env.opts.autoescape);
output += "</div>\n\t\t</div>\n\n\t</div>";
;
}
}
frame = frame.pop();
output += "</div>\n\n";
if(parentTemplate) {
parentTemplate.rootRenderFunc(env, context, frame, runtime, cb);
} else {
cb(null, output);
}
;
} catch (e) {
  cb(runtime.handleError(e, lineno, colno));
}
}
return {
root: root
};

})();
})();
(function() {(window.nunjucksPrecompiled = window.nunjucksPrecompiled || {})["directory-list.html"] = (function() {
function root(env, context, frame, runtime, cb) {
var lineno = null;
var colno = null;
var output = "";
try {
var parentTemplate = null;
output += "<table id=\"dir\" class=\"table table-striped table-hover\" style=\"width: 100%\">\n\t<thead>\n\t\t<tr>\n\t\t\t<th class=\"tsdisable\" style=\"width: 1px\"></th>\n\t\t\t<th>Name</th>\n\t\t\t<th class=\"hidden-xs hidden-sm\">Modified</th>\n\t\t\t<th></th>\n\t\t\t<th></th>\n\t\t\t<th></th>\n\t\t\t<th></th>\n\t\t</tr>\n\t</thead>\n\t<tbody>";
frame = frame.push();
var t_3 = runtime.contextOrFrameLookup(context, frame, "shares");
if(t_3) {var t_2 = t_3.length;
for(var t_1=0; t_1 < t_3.length; t_1++) {
var t_4 = t_3[t_1];
frame.set("entry", t_4);
frame.set("loop.index", t_1 + 1);
frame.set("loop.index0", t_1);
frame.set("loop.revindex", t_2 - t_1);
frame.set("loop.revindex0", t_2 - t_1 - 1);
frame.set("loop.first", t_1 === 0);
frame.set("loop.last", t_1 === t_2 - 1);
frame.set("loop.length", t_2);
output += "<tr class=\"edir\" data-url=\"";
output += runtime.suppressValue((lineno = 14, colno = 38, runtime.callWrap(runtime.contextOrFrameLookup(context, frame, "buildurl"), "buildurl", context, [runtime.memberLookup((t_4),"burl"),runtime.memberLookup((t_4),"name"),"browse"])), env.opts.autoescape);
output += "\">\n\t\t\t<td class=\"text-center\"><span class=\"fa fa-fw fa-hdd-o\"></span></td>\n\t\t\t<td class=\"dentry\">";
output += runtime.suppressValue(runtime.memberLookup((t_4),"name"), env.opts.autoescape);
output += "</td>\n\t\t\t<td class=\"hidden-xs hidden-sm dentry-mtime\"></td>\n\t\t\t<td>";
output += runtime.suppressValue(runtime.memberLookup((t_4),"name"), env.opts.autoescape);
output += "</td>\n\t\t\t<td></td>\n\t\t\t<td></td>\n\t\t\t<td></td>\n\t\t</tr>";
;
}
}
frame = frame.pop();
frame = frame.push();
var t_7 = runtime.contextOrFrameLookup(context, frame, "dirs");
if(t_7) {var t_6 = t_7.length;
for(var t_5=0; t_5 < t_7.length; t_5++) {
var t_8 = t_7[t_5];
frame.set("entry", t_8);
frame.set("loop.index", t_5 + 1);
frame.set("loop.index0", t_5);
frame.set("loop.revindex", t_6 - t_5);
frame.set("loop.revindex0", t_6 - t_5 - 1);
frame.set("loop.first", t_5 === 0);
frame.set("loop.last", t_5 === t_6 - 1);
frame.set("loop.length", t_6);
output += "<tr class=\"edir\" data-icon=\"fa fa-fw fa-folder\" data-url=\"";
output += runtime.suppressValue((lineno = 25, colno = 69, runtime.callWrap(runtime.contextOrFrameLookup(context, frame, "buildurl"), "buildurl", context, [runtime.memberLookup((t_8),"burl"),runtime.memberLookup((t_8),"path"),"browse"])), env.opts.autoescape);
output += "\" data-filename=\"";
output += runtime.suppressValue(runtime.memberLookup((t_8),"name"), env.opts.autoescape);
output += "\" data-stat=\"";
output += runtime.suppressValue(runtime.memberLookup((t_8),"stat"), env.opts.autoescape);
output += "\">\n\t\t\t<td class=\"text-center\"><span class=\"fa fa-fw fa-folder\"></span></td>\n\t\t\t<td class=\"dentry\">";
output += runtime.suppressValue(runtime.memberLookup((t_8),"name"), env.opts.autoescape);
output += "</td>\n\t\t\t<td class=\"hidden-xs hidden-sm dentry-mtime\">-</td>\n\t\t\t<td>.1111";
output += runtime.suppressValue(runtime.memberLookup((t_8),"name"), env.opts.autoescape);
output += "</td>\n\t\t\t<td>-1</td>\n\t\t\t<td>111adir</td>\n\t\t\t<td>-1</td>\n\t\t</tr>";
;
}
}
frame = frame.pop();
frame = frame.push();
var t_11 = runtime.contextOrFrameLookup(context, frame, "files");
if(t_11) {var t_10 = t_11.length;
for(var t_9=0; t_9 < t_11.length; t_9++) {
var t_12 = t_11[t_9];
frame.set("entry", t_12);
frame.set("loop.index", t_9 + 1);
frame.set("loop.index0", t_9);
frame.set("loop.revindex", t_10 - t_9);
frame.set("loop.revindex0", t_10 - t_9 - 1);
frame.set("loop.first", t_9 === 0);
frame.set("loop.last", t_9 === t_10 - 1);
frame.set("loop.length", t_10);
output += "<tr class=\"efile\" data-icon=\"fa fa-fw fa-";
output += runtime.suppressValue(runtime.memberLookup((t_12),"icon"), env.opts.autoescape);
output += "\" ";
if(runtime.memberLookup((t_12),"img")) {
output += "data-img=\"true\" ";
;
}
output += " ";
if(runtime.memberLookup((t_12),"view")) {
output += "data-view=\"true\"";
;
}
output += " data-mtype=\"";
output += runtime.suppressValue(runtime.memberLookup((t_12),"mtype"), env.opts.autoescape);
output += "\" data-filename=\"";
output += runtime.suppressValue(runtime.memberLookup((t_12),"name"), env.opts.autoescape);
output += "\" data-mtime=\"";
output += runtime.suppressValue(runtime.memberLookup((t_12),"mtime"), env.opts.autoescape);
output += "\" data-size=\"";
output += runtime.suppressValue(env.getFilter("filesizeformat").call(context, runtime.memberLookup((t_12),"size"),runtime.makeKeywordArgs({"binary": runtime.contextOrFrameLookup(context, frame, "True")})), env.opts.autoescape);
output += "\" data-path=\"";
output += runtime.suppressValue(runtime.memberLookup((t_12),"path"), env.opts.autoescape);
output += "\" data-burl=\"";
output += runtime.suppressValue(runtime.memberLookup((t_12),"burl"), env.opts.autoescape);
output += "\">\n\t\t\t<td class=\"text-center\"><span class=\"fa fa-fw fa-";
output += runtime.suppressValue(runtime.memberLookup((t_12),"icon"), env.opts.autoescape);
output += "\"></span></td>\n\t\t\t<td class=\"dentry\">";
output += runtime.suppressValue(runtime.memberLookup((t_12),"name"), env.opts.autoescape);
output += "</td>\n\t\t\t<td class=\"hidden-xs hidden-sm dentry-mtime\">";
output += runtime.suppressValue(runtime.memberLookup((t_12),"mtime"), env.opts.autoescape);
output += "</td>\n\t\t\t<td>";
output += runtime.suppressValue(runtime.memberLookup((t_12),"name"), env.opts.autoescape);
output += "</td>\n\t\t\t<td>";
output += runtime.suppressValue(runtime.memberLookup((t_12),"mtimer"), env.opts.autoescape);
output += "</td>\n\t\t\t<td>";
output += runtime.suppressValue(runtime.memberLookup((t_12),"mtyper"), env.opts.autoescape);
output += "</td>\n\t\t\t<td>";
output += runtime.suppressValue(runtime.memberLookup((t_12),"size"), env.opts.autoescape);
output += "</td>\n\t\t</tr>";
;
}
}
frame = frame.pop();
output += "</tbody>\n</table>\n";
if(parentTemplate) {
parentTemplate.rootRenderFunc(env, context, frame, runtime, cb);
} else {
cb(null, output);
}
;
} catch (e) {
  cb(runtime.handleError(e, lineno, colno));
}
}
return {
root: root
};

})();
})();
(function() {(window.nunjucksPrecompiled = window.nunjucksPrecompiled || {})["empty.html"] = (function() {
function root(env, context, frame, runtime, cb) {
var lineno = null;
var colno = null;
var output = "";
try {
var parentTemplate = null;
output += "<p>\n<div class=\"jumbotron no-items\">\n\t<h1><span class=\"fa fa-fw fa-3x fa-folder-open-o\"></span></h1>\n\t<p><strong>there are no items in this folder</strong><br/>\n\t<span class=\"hidden-xs\">click and drag a file here to upload</span></p>\n\t</div>\n</p>\n";
if(parentTemplate) {
parentTemplate.rootRenderFunc(env, context, frame, runtime, cb);
} else {
cb(null, output);
}
;
} catch (e) {
  cb(runtime.handleError(e, lineno, colno));
}
}
return {
root: root
};

})();
})();
(function() {(window.nunjucksPrecompiled = window.nunjucksPrecompiled || {})["search.html"] = (function() {
function root(env, context, frame, runtime, cb) {
var lineno = null;
var colno = null;
var output = "";
try {
var parentTemplate = null;
output += "<h3>Results for '";
output += runtime.suppressValue(runtime.contextOrFrameLookup(context, frame, "query"), env.opts.autoescape);
output += "'</h3>\n";
if(runtime.contextOrFrameLookup(context, frame, "timeout_reached")) {
output += "\n<div class=\"alert alert-dismissable alert-warning\"><button type=\"button\" class=\"close\" data-dismiss=\"alert\">×</button>Some search results have been omitted because the search took too long to perform</div>\n";
;
}
output += "\n<table id=\"results\" class=\"table table-striped table-hover\" style=\"width: 100%\">\n\t<thead>\n\t\t<tr>\n\t\t\t<th class=\"tsdisable\" style=\"width: 1px\"></th>\n\t\t\t<th>Name</th>\n\t\t</tr>\n\t</thead>\n\t<tbody>";
frame = frame.push();
var t_3 = runtime.contextOrFrameLookup(context, frame, "results");
if(t_3) {var t_2 = t_3.length;
for(var t_1=0; t_1 < t_3.length; t_1++) {
var t_4 = t_3[t_1];
frame.set("entry", t_4);
frame.set("loop.index", t_1 + 1);
frame.set("loop.index0", t_1);
frame.set("loop.revindex", t_2 - t_1);
frame.set("loop.revindex0", t_2 - t_1 - 1);
frame.set("loop.first", t_1 === 0);
frame.set("loop.last", t_1 === t_2 - 1);
frame.set("loop.length", t_2);
if(runtime.memberLookup((t_4),"type") == 7) {
output += "\n\t\t<tr class=\"edir\" data-url=\"";
output += runtime.suppressValue(runtime.memberLookup((t_4),"url"), env.opts.autoescape);
output += "\">\n\t\t";
;
}
else {
if(runtime.memberLookup((t_4),"type") == 8) {
output += "\n\t\t<tr class=\"efile\" data-icon=\"fa fa-fw fa-";
output += runtime.suppressValue(runtime.memberLookup((t_4),"icon"), env.opts.autoescape);
output += "\" ";
if(runtime.memberLookup((t_4),"img")) {
output += "data-img=\"true\" ";
;
}
output += " data-mtype=\"";
output += runtime.suppressValue(runtime.memberLookup((t_4),"mtype"), env.opts.autoescape);
output += "\" data-filename=\"";
output += runtime.suppressValue(runtime.memberLookup((t_4),"name"), env.opts.autoescape);
output += "\" data-mtime=\"";
output += runtime.suppressValue(runtime.memberLookup((t_4),"mtime"), env.opts.autoescape);
output += "\" data-size=\"";
output += runtime.suppressValue(env.getFilter("filesizeformat").call(context, runtime.memberLookup((t_4),"size"),runtime.makeKeywordArgs({"binary": runtime.contextOrFrameLookup(context, frame, "True")})), env.opts.autoescape);
output += "\" data-burl=\"";
output += runtime.suppressValue(runtime.memberLookup((t_4),"burl"), env.opts.autoescape);
output += "\" data-path=\"";
output += runtime.suppressValue(runtime.memberLookup((t_4),"path"), env.opts.autoescape);
output += "\" ";
if(runtime.memberLookup((t_4),"view")) {
output += "data-view=\"true\"";
;
}
output += ">\n\t\t\t<td class=\"text-center\"><span class=\"";
output += runtime.suppressValue(runtime.memberLookup((t_4),"icon"), env.opts.autoescape);
output += " fa-2x\"></span></td>\n\t\t\t<td class=\"dentry\">";
output += runtime.suppressValue(runtime.memberLookup((t_4),"name"), env.opts.autoescape);
output += "<br/>\n\t\t\t\t<span class=\"text-muted\">in <a class=\"edir\" data-url=\"";
output += runtime.suppressValue(runtime.memberLookup((t_4),"parent_url"), env.opts.autoescape);
output += "\">";
if(runtime.memberLookup((t_4),"parent_path")) {
output += " /";
output += runtime.suppressValue(runtime.memberLookup((t_4),"parent_path"), env.opts.autoescape);
;
}
else {
output += runtime.suppressValue(runtime.contextOrFrameLookup(context, frame, "root_display_name"), env.opts.autoescape);
;
}
output += "</a></span>\n\t\t\t</td>\n\t\t";
;
}
;
}
output += "\n\t\t</tr>";
;
}
}
if (!t_2) {
output += "<tr><td colspan=\"2\"><em>No results found</em></td></tr>\n\t\t";
}
frame = frame.pop();
output += "\n\t</tbody>\n</table>\n";
if(parentTemplate) {
parentTemplate.rootRenderFunc(env, context, frame, runtime, cb);
} else {
cb(null, output);
}
;
} catch (e) {
  cb(runtime.handleError(e, lineno, colno));
}
}
return {
root: root
};

})();
})();

