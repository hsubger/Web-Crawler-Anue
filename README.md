# Web-Crawler-Anue
因為檔案大小關係anue.sqlite3是空白資料庫，可至我的google雲端硬碟 https://reurl.cc/E7DOok 下載 anue_資料時間至20200601.sqlite3，此資料庫有至2020/06/01示範資料。
使用 selenium 套件模擬操作 Chrome 進入鉅亨網全部新聞網頁，點選日期輸入框選擇前一天日期，滾動頁面載入所有內容，程式會將所有前一日資料全部抓取並儲存於 anue.sqlite3 資料庫。由於這個程式設計是在隔天回去抓取前一天的所有程式，可透過.bat檔，安排工作排程達成每日自動抓取資料。
ps. 批次檔中full_path必須改為此檔案資料夾完整路徑後才可執行
