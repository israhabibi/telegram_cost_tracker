var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0]; // Gets the first sheet of the active spreadsheet

function doGet(e) {
  try {
    var action = e.parameter.action;
    var targetDateStr = e.parameter.date; // Format YYYY-MM-DD

    if (action == "get_daily" && targetDateStr) {
      var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];

      // Asumsi kolom tanggal ada di kolom A (index 1)
      // Asumsi data dimulai dari baris 2 (setelah header)
      var dataRange = sheet.getDataRange();
      var values = dataRange.getValues();
      var header = values[0]; // Ambil header untuk mencocokkan nama kolom
      var dateColIndex = header.indexOf("Tanggal") + 1; // Cari index kolom 'Tanggal' (sesuaikan namanya)
      var amountColIndex = header.indexOf("Amount") + 1; // Cari index kolom 'Amount'
      var descColIndex = header.indexOf("Description") + 1;
      var categoryColIndex = header.indexOf("Category") + 1;
      var paymentColIndex = header.indexOf("Payment Method") + 1;


      if (dateColIndex === 0 || amountColIndex === 0) {
         throw new Error("Kolom 'Tanggal' atau 'Amount' tidak ditemukan di header.");
      }

      var dailyExpenses = [];
      var totalToday = 0;
      var targetDate = new Date(targetDateStr + "T00:00:00"); // Pastikan perbandingan tanggal benar

      // Loop mulai dari baris kedua (index 1)
      for (var i = 1; i < values.length; i++) {
        var row = values[i];
        var cellValue = row[dateColIndex - 1]; // Index berbasis 0
        var rowDate;

        // Cek apakah cellValue adalah objek Date atau string
        if (cellValue instanceof Date) {
          rowDate = cellValue;
        } else if (typeof cellValue === 'string' && cellValue.length > 0) {
           try {
             rowDate = new Date(cellValue);
             if (isNaN(rowDate.getTime())) { // Cek jika parsing gagal
                Logger.log("Invalid date string in row " + (i+1) + ": " + cellValue);
                continue; // Lewati baris ini jika tanggal tidak valid
             }
           } catch (err) {
             Logger.log("Error parsing date in row " + (i+1) + ": " + cellValue + ", Error: " + err);
             continue; // Lewati baris ini
           }
        } else {
           Logger.log("Skipping row " + (i+1) + " due to empty or invalid date cell.");
           continue; // Lewati jika sel tanggal kosong atau tipe tidak dikenal
        }

        // Normalisasi tanggal ke awal hari untuk perbandingan
        var normalizedRowDate = new Date(rowDate.getFullYear(), rowDate.getMonth(), rowDate.getDate());
        var normalizedTargetDate = new Date(targetDate.getFullYear(), targetDate.getMonth(), targetDate.getDate());


        if (normalizedRowDate.getTime() === normalizedTargetDate.getTime()) {
          var amount = parseFloat(row[amountColIndex - 1]) || 0;
          dailyExpenses.push({
            description: row[descColIndex - 1] || 'N/A',
            amount: amount,
            category: row[categoryColIndex - 1] || '',
            payment_method: row[paymentColIndex - 1] || ''
            // Tambahkan field lain jika perlu
          });
          totalToday += amount;
        }
      }

      var result = {
        status: "success",
        date: targetDateStr,
        expenses: dailyExpenses,
        total: totalToday
      };
      return ContentService.createTextOutput(JSON.stringify(result))
                         .setMimeType(ContentService.MimeType.JSON);

    } else {
      // Handle other actions or invalid requests
      return ContentService.createTextOutput(JSON.stringify({status: "error", message: "Aksi tidak valid atau tanggal tidak disediakan."}))
                         .setMimeType(ContentService.MimeType.JSON);
    }

  } catch (error) {
    Logger.log(error); // Log error ke Apps Script Logger
    return ContentService.createTextOutput(JSON.stringify({status: "error", message: "Terjadi kesalahan di server: " + error.message}))
                       .setMimeType(ContentService.MimeType.JSON);
  }
}

// Fungsi doPost Anda yang sudah ada untuk menyimpan data
function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];

    var data = JSON.parse(e.postData.contents);

    // Pastikan kolom Amount adalah angka
    var amount = parseFloat(data.amount);
    if (isNaN(amount)) {
      amount = 0; // Atau handle error jika amount tidak valid
    }

    // Tambahkan timestamp saat data dimasukkan
    var timestamp = new Date();

    // Sesuaikan urutan kolom dengan sheet Anda
    sheet.appendRow([
      timestamp, // Kolom A: Tanggal (Otomatis)
      amount, // Kolom B: Amount
      data.description, // Kolom C: Description
      data.payment_method, // Kolom D: Payment Method
      data.category // Kolom E: Category
      // Tambahkan kolom lain jika ada
    ]);

    return ContentService.createTextOutput(JSON.stringify({status: "success", message: "Data berhasil ditambahkan"}))
                       .setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    Logger.log(error);
    return ContentService.createTextOutput(JSON.stringify({status: "error", message: "Gagal menyimpan data: " + error.message}))
                       .setMimeType(ContentService.MimeType.JSON);
  }
}
