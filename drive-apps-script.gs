// AgroData -> Google Drive bridge (Apps Script Web App) — v2
// Saves each deliverable as a readable Google Doc in your Agro-Tech folder,
// lists them for the site, returns a single doc's TEXT (for feeding back into
// the analysis), and stores a category/topic per file. Runs as you.

var FOLDER_ID = '1njNNrpOD5DFySYX-VaRZ5WFS-MlnU15Q';

function doPost(e) {
  try {
    var d = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    var folder = DriveApp.getFolderById(FOLDER_ID);

    if (d.action === 'delete' && d.id) {
      DriveApp.getFileById(d.id).setTrashed(true);
      return _json({ ok: true });
    }

    var title = (d.title && String(d.title).trim()) || ('AgroData deliverable ' + _today());
    var doc = DocumentApp.create(title);
    var body = doc.getBody();
    body.appendParagraph(title).setHeading(DocumentApp.ParagraphHeading.HEADING1);
    body.appendParagraph((d.by || 'AgroData AI') + (d.cat ? ('  -  ' + d.cat) : '') + '  -  ' + _today());
    body.appendParagraph('');
    body.appendParagraph(String(d.note || ''));
    doc.saveAndClose();

    var file = DriveApp.getFileById(doc.getId());
    folder.addFile(file);
    try { DriveApp.getRootFolder().removeFile(file); } catch (x) {}
    if (d.cat) { try { file.setDescription('cat:' + d.cat); } catch (x) {} }

    return _json({ ok: true, id: file.getId(), url: file.getUrl(), title: title });
  } catch (err) {
    return _json({ ok: false, error: String(err) });
  }
}

function doGet(e) {
  try {
    // single doc's text content (for pulling back into the analysis)
    var id = e && e.parameter && e.parameter.id;
    if (id) {
      var text = '';
      try { text = DocumentApp.openById(id).getBody().getText(); } catch (x) { text = ''; }
      return _json({ ok: true, id: id, content: text });
    }

    var folder = DriveApp.getFolderById(FOLDER_ID);
    var it = folder.getFiles(), out = [];
    while (it.hasNext()) {
      var f = it.next();
      var cat = 'תוצר', desc = '';
      try { desc = f.getDescription() || ''; } catch (x) {}
      if (desc.indexOf('cat:') === 0) cat = desc.substring(4);
      out.push({
        id: f.getId(),
        title: f.getName(),
        url: f.getUrl(),
        cat: cat,
        by: 'AgroData AI',
        ts: Math.floor(f.getDateCreated().getTime() / 1000)
      });
    }
    out.sort(function (a, b) { return b.ts - a.ts; });
    return _json({ ok: true, docs: out });
  } catch (err) {
    return _json({ ok: false, error: String(err), docs: [] });
  }
}

function _today() {
  return Utilities.formatDate(new Date(), 'Asia/Jerusalem', 'dd.MM.yyyy');
}
function _json(o) {
  return ContentService.createTextOutput(JSON.stringify(o))
    .setMimeType(ContentService.MimeType.JSON);
}
