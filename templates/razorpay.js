function doPost(e) {
    try {
      var ss = SpreadsheetApp.getActiveSpreadsheet();
      var sheet = ss.getSheetByName("Admissions");
      if (!sheet) sheet = ss.insertSheet("Admissions");
  
      var data = JSON.parse(e.postData.contents);
      sheet.appendRow([
        new Date(),
        data.name || "",
        data.email || "",
        data.phone || "",
        data.amount || "",
        data.payment_id || ""
      ]);
      return ContentService.createTextOutput(JSON.stringify({status: "success"})).setMimeType(ContentService.MimeType.JSON);
    } catch (err) {
      return ContentService.createTextOutput(JSON.stringify({status: "error", message: err.message})).setMimeType(ContentService.MimeType.JSON);
    }
  }
  