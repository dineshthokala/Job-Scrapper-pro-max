/**
 * Google Apps Script for Job Scraper -> Google Sheets Sync
 * 
 * Instructions:
 * 1. Open a new Google Sheet (e.g. named "Flutter Job Hunt Tracker").
 * 2. In row 1, set up the column headers:
 *    A1: Date | B1: Title | C1: Company | D1: Location | E1: Source | F1: Job URL | G1: Status | H1: Notes
 * 3. In Google Sheets, click: Extensions -> Apps Script.
 * 4. Delete any code in the editor and PASTE THIS ENTIRE SCRIPT.
 * 5. Click the blue "Deploy" button (top right) -> "New deployment".
 * 6. Click the gear icon next to "Select type" -> choose "Web app".
 * 7. Set:
 *    - Description: Job Scraper Sync
 *    - Execute as: Me (your email)
 *    - Who has access: Anyone  <-- (IMPORTANT: Must be "Anyone" so the scraper can post data)
 * 8. Click "Deploy", authorize permissions when prompted, and COPY the "Web app URL".
 * 9. Add that URL to your .env file as:
 *    GOOGLE_SHEET_WEBHOOK_URL=https://script.google.com/macros/s/.../exec
 *    (and add it as a Secret named GOOGLE_SHEET_WEBHOOK_URL in GitHub repo settings!)
 */

function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var data = JSON.parse(e.postData.contents);
    
    // Check if header exists, if not create it
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(["Date", "Title", "Company", "Location", "Source", "Job URL", "Status", "Notes"]);
      sheet.getRange("A1:H1").setFontWeight("bold").setBackground("#202124").setFontColor("#ffffff");
    }

    // Append new job row
    sheet.appendRow([
      data.date || new Date().toISOString(),
      data.title || "",
      data.company || "",
      data.location || "",
      data.source || "",
      data.url || "",
      "New",      // Default Status
      ""          // Notes (empty for you to fill)
    ]);
    
    return ContentService.createTextOutput(JSON.stringify({ "status": "success" }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({ "status": "error", "message": error.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService.createTextOutput("Google Sheets Webhook Active")
    .setMimeType(ContentService.MimeType.TEXT);
}

