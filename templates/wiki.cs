<?cs set:html.stylesheet = 'css/wiki.css' ?>
<?cs include "header.cs" ?>
<?cs include "macros.cs" ?>

<div id="ctxtnav" class="nav">
 <h2>Wiki Navigation</h2>
 <ul>
  <li><a href="<?cs var:$trac.href.wiki ?>">Start Page</a></li>
  <li><a href="<?cs var:$trac.href.wiki ?>/TitleIndex">Title Index</a></li>
  <li><a href="<?cs var:$trac.href.wiki ?>/RecentChanges">Recent Changes</a></li>
  <?cs if:wiki.history_href ?>
   <li class="last"><a href="<?cs var:wiki.history_href ?>">Page History</a></li>
  <?cs else ?>
   <li class="last">Page History</li>
  <?cs /if ?>
 </ul>
 <hr />
</div>

<div id="content" class="wiki">

 <?cs if:wiki.action == "diff" ?>
  <h1>Changes in version <?cs var:wiki.edit_version?> of <a href="<?cs
    var:wiki.current_href ?>"><?cs var:wiki.page_name ?></a></h1>
   <form id="prefs" action="<?cs var:wiki.current_href ?>">
    <input type="hidden" name="version" value="<?cs var:wiki.version ?>" />
    <input type="hidden" name="diff" value="yes" />
    <div>
     <label for="type">View differences</label>
     <select name="style" onchange="this.form.submit()">
      <option value="inline"<?cs
        if:diff.style == 'inline' ?> selected="selected"<?cs
        /if ?>>inline</option>
      <option value="sidebyside"<?cs
        if:diff.style == 'sidebyside' ?> selected="selected"<?cs
        /if ?>>side by side</option>
     </select>
     <div class="buttons">
      <input type="submit" name="update" value="Update" />
     </div>
    </div>
   </form>
   <dl id="overview">
    <dt class="author">Author:</dt>
    <dd><?cs var:wiki.diff.author ?></dd>
    <dt class="time">Timestamp:</dt>
    <dd><?cs var:wiki.diff.time ?></dd>
    <?cs if:wiki.diff.comment ?>
     <dt class="comment">Comment:</dt>
     <dd><?cs var:wiki.diff.comment ?></dd>
    <?cs /if ?>
   </dl>

   <div class="diff">
    <div id="legend">
     <h3>Legend:</h3>
     <dl>
      <dt class="unmod"></dt><dd>Unmodified</dd>
      <dt class="add"></dt><dd>Added</dd>
      <dt class="rem"></dt><dd>Removed</dd>
      <dt class="mod"></dt><dd>Modified</dd>
     </dl>
    </div>
    <ul>
     <li>
      <h2><?cs var:wiki.diff.name.new ?></h2>
      <?cs if:diff.style == 'sidebyside' ?>
       <table class="sidebyside" summary="Differences">
        <colgroup class="base">
         <col class="lineno" /><col class="content" />
        <colgroup class="chg">
         <col class="lineno" /><col class="content" />
        </colgroup>
        <thead><tr>
         <th colspan="2">Version <?cs var:wiki.diff.rev.old ?></th>
         <th colspan="2">Version <?cs var:wiki.diff.rev.new ?></th>
        </tr></thead>
        <?cs each:change = wiki.diff.changes ?>
         <tbody>
          <?cs call:diff_display(change, diff.style) ?>
         </tbody>
        <?cs /each ?>
       </table>
      <?cs else ?>
       <table class="inline" summary="Differences">
        <colgroup>
         <col class="lineno" />
         <col class="lineno" />
         <col class="content" />
        </colgroup>
        <thead><tr>
         <th title="Version <?cs var:wiki.diff.rev.old ?>">v<?cs
           var:wiki.diff.rev.old ?></th>
         <th title="Version <?cs var:wiki.diff.rev.new ?>">v<?cs
           var:wiki.diff.rev.new ?></th>
         <th></th>
        </tr></thead>
        <?cs each:change = wiki.diff.changes ?>
         <?cs call:diff_display(change, diff.style) ?>
        <?cs /each ?>
       </table>
      <?cs /if ?>
     </li>
    </ul>
   </div>
 
 <?cs elif wiki.action == "history" ?>
  <h1>Change History of <a href="<?cs var:wiki.current_href ?>"><?cs
    var:wiki.page_name ?></a></h1>
  <?cs if:wiki.history ?>
   <table id="wikihist" class="listing" summary="Change history">
    <thead><tr>
     <th class="date">Date</th>
     <th class="version">Version</th>
     <th class="author">Author</th>
     <th class="comment">Comment</th>
    </tr></thead>
    <tbody><?cs each:item = wiki.history ?>
     <tr class="<?cs if:name(item) % #2 ?>even<?cs else ?>odd<?cs /if ?>">
      <td class="date"><?cs var:$item.time ?></td>
      <td class="version">
       <a href="<?cs var:item.url ?>" title="View version"><?cs
         var:item.version ?></a>
       (<a href="<?cs var:item.diff_url ?>" title="Compare to previous version">diff</a>)
      </td>
      <td class="author">
       <span class="name"><?cs var:$item.author ?></span>
       <span class="ipaddr">(IP: <?cs var:$item.ipaddr ?>)</span>
      </td>
      <td class="comment"><?cs var:$item.comment ?></td>
     </tr>
    <?cs /each ?></tbody>
   </table>
  <?cs /if ?>
 
 <?cs else ?>
   <?cs if wiki.action == "edit" || wiki.action == "preview" ?>
    <h3>Editing "<?cs var:wiki.page_name ?>"</h3>
     <form action="<?cs var:wiki.current_href ?>#preview" method="post">
      <div style="width: 100%">
       <input type="hidden" name="edit_version"
           value="<?cs var:wiki.edit_version?>" />
       <label for="text">Page source:</label><br />
       <textarea id="text" name="text" rows="20" cols="80"
           style="width: 97%"><?cs var:wiki.page_source ?></textarea>
       <?cs call:wiki_toolbar('text') ?>
       <div id="help">
       <b>Note:</b> See <a href="<?cs var:$trac.href.wiki
?>/WikiFormatting">WikiFormatting</a> and <a href="<?cs var:$trac.href.wiki
?>/TracWiki">TracWiki</a> for help on editing wiki content.
       </div>
       <fieldset>
         <legend>Change information</legend>
         <div style="display: inline; float: left; margin: 0 .5em;">
           <label for="author">Your email or username:</label><br />
           <input id="author" type="text" name="author" size="30"
                value="<?cs call:session_name_email() ?>"/>
         </div>
         <div>
           <label for="comment">Comment about this change (optional):</label>
           <br />
           <input id="comment" type="text" name="comment" size="60"
                 value="<?cs var:wiki.comment?>" />
         </div>
	 <?cs if trac.acl.WIKI_ADMIN ?>
	 <div>
	   <input type="checkbox" name="readonly"
           <?cs if wiki.readonly == "1"?>checked="checked"<?cs /if ?> /> Page is read-only.
	 </div>
	 <?cs /if ?>
         <div class="buttons">
             <input type="submit" name="save" value="Save changes" />&nbsp;
             <input type="submit" name="preview" value="Preview" />&nbsp;
             <input type="submit" name="cancel" value="Cancel" />
	     <?cs if trac.acl.WIKI_ADMIN ?>
	         &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                <input type="submit" name="delete_ver" value="Delete this version"
                       onClick="return confirm('Do you really want to delete version <?cs var:wiki.edit_version?>?\nThis is an irreversible operation.')"/>
                 <input type="submit" name="delete_page" value="Delete Page" 
                        onClick="return confirm('Do you really want to delete all versions of this page?\nThis is an irreversible operation.')"/>
	     <?cs /if ?>
         </div>
       </fieldset>
      </div>
     </form>
   <?cs /if ?>
   <?cs if wiki.action == "view" || wiki.action == "preview" ?>
     <?cs if wiki.action == "preview" ?><hr /><?cs /if ?>
     <a name="preview" />
     <div class="wikipage">
         <div id="searchable">
          <?cs var:wiki.page_html ?>
         </div>
     </div>
   <?cs if $wiki.attachments.0.name ?>
    <h3 id="tkt-changes-hdr">Attachments</h3>
    <ul class="tkt-chg-list">
    <?cs each:a = wiki.attachments ?>
      <li class="tkt-chg-change"><a href="<?cs var:a.href ?>">
      <?cs var:a.name ?></a> (<?cs var:a.size ?>) -
      <?cs var:a.descr ?>,
      added by <?cs var:a.author ?> on <?cs var:a.time ?>.</li>
    <?cs /each ?>
  </ul>
  <?cs /if ?>
  <?cs if wiki.action == "view" && trac.acl.WIKI_MODIFY &&
       (wiki.readonly == "0" || trac.acl.WIKI_ADMIN) ?>
       <form class="inline" method="get" action=""><div>
        <input type="hidden" name="edit" value="yes" />
        <input type="submit" value="Edit This Page" />
       </div></form>
       <form class="inline" method="get" action="<?cs
              var:cgi_location?>/attachment/wiki/<?cs
              var:wiki.namedoublequoted ?>"><div>
        <input type="submit" value="Attach File" />
       </div></form>
     <?cs /if ?>
   <?cs /if ?>
 <?cs /if ?>

</div>
<?cs include "footer.cs" ?>
