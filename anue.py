from selenium import webdriver
from bs4 import BeautifulSoup
import time
import datetime
import sqlite3

'''
使用 selenium 套件模擬操作 Chrome 進入鉅亨網全部新聞網頁，點選日期輸入框選擇前一天日期，
滾動頁面載入所有內容，程式會將所有前一日資料全部抓取並儲存於 anue.sqlite3 資料庫，
目前亦有規劃移轉至 GCP 的資料庫中。
由於這個程式設計是在隔天回去抓取前一天的所有程式，所以我也建立了一個批次檔，透過工作排成的安排達成每日自動抓取資料
ps. 批次檔中full_path必須改為此檔案資料夾完整路徑後才可執行
'''

def setWebdriver():
    '''建立webdeiver物件，並禁止彈出式視窗'''
    chrome_options=webdriver.ChromeOptions()
    prefs={"profile.default_content_setting_values.notifications":2}
    chrome_options.add_experimental_option("prefs",prefs)
    '''背景執行'''
    chrome_options.add_argument("--headless")
    driver=webdriver.Chrome(options=chrome_options)
    return driver

def openPage(url, driver):
    '''載入網站'''
    driver.get(url)
    driver.implicitly_wait(20)
    return driver

def yesterDate():
    '''昨天等於今天加負一天'''
    yesterday = datetime.date.today() + datetime.timedelta(-1)
    a = str(yesterday).split("-")
    return int(a[2])

def makeDate(driver, yesterD):
    '''點擊日期輸入框'''
    driver.find_element_by_css_selector('._Qfx4 input').click()
    '''取得所有日期'''
    a = driver.find_elements_by_css_selector('.react-date-picker__month-view-day-text')
    '''找出前一日日期所在位置'''
    resultP = []
    for i in range(len(a)):
        '''日曆中一次兩個月，第二個月的yesterD為目標日期'''
        if a[i].text == str(yesterD): resultP.append(i)#找出日對的地方
    '''點擊兩次目標日期'''
    if len(resultP) == 2:
        a[resultP[1]].click()
        a[resultP[1]].click()
    elif len(resultP) == 3 and yesterD <15:
        a[resultP[1]].click()
        a[resultP[1]].click()
    elif len(resultP) == 3 and yesterD >=15:
        a[resultP[-1]].click()
        a[resultP[-1]].click()
    driver.find_element_by_css_selector('.react-date-picker__footer-button').click()
    return driver

def scrollGetHtml(driver):
    '''頁面向下向上來回捲動，載入所有資料'''
    for i in range(100):
        driver.execute_script("var action=document.documentElement.scrollTop=10000")
        driver.implicitly_wait(20)
        driver.execute_script("var action=document.documentElement.scrollTop=0")
        driver.implicitly_wait(20)
        driver.execute_script("window.scrollTo(0,document.body.scrollHeight);")
        driver.implicitly_wait(20)
        driver.execute_script("var action=document.documentElement.scrollTop=0")
        driver.implicitly_wait(20)
        time.sleep(0.2)
    '''取得網頁原始碼'''
    soup=BeautifulSoup(driver.page_source,'html.parser')
    #page=soup.select('.theme-list')
    page=soup.find_all("div",{"style":"height: 70px;"})
    return driver,page

def pageClean(page):
    '''將頁面資料整理成[YMD,HMN,classStr,title,href,classCode]'''
    cleanData = []
    for i in page:
        notClean = str(i)
        dateAll = notClean.split('datetime="')[1].split('+')[0]
        YMD, HMN = dateAll.split('T')[0], dateAll.split('T')[1]
        classStr = notClean.split('theme-sub-cat">')[1].split('<')[0]
        title = notClean.split('title="')[1].split('"')[0]
        fHref = 'https://news.cnyes.com'
        href = fHref + notClean.split('href="')[1].split('"')[0]
        classCode = notClean.split('data-exp-id="')[1].split('"')[0]
        cleanData.append([YMD,HMN,classStr,title,href,classCode])
    return cleanData


def hrefTagContent(hrefC):  #hrefC為字典類型資料
    '''取得連結標籤及文章'''
    # 設定Webdriver
    driver = setWebdriver()
    lod = 1#第lod篇文章

    '''
    讀取造成文章段落整理時產生無限迴圈的可能原因
    '''
    with open('makeRepeat.txt', 'r') as f:
        reasons = f.readlines()
    reasonDict = {}#儲存可能原因的字典
    for r in reasons:
        r = r.strip('\n')
        reasonDict[ r.split(',')[0] ] = r.split(',')[1] if r.split(',')[1]!='()' else ''
    #print(reasonDict)
    
    #keyHref是dict檔案hrefC的key, 為所有的文章連結
    for keyHref in hrefC.keys():
        rec1 = "\t文章{:^3d}/{:^3d} ".format(lod, len(hrefC))
        print(rec1, end = ' ')
        lod+=1
        startC = time.time()
        driver = openPage(keyHref, driver)
        soup=BeautifulSoup(driver.page_source,'html.parser')
        tagL = []#儲存tag的list
        content = []
        
        # 取出tag
        a = str( soup.find_all("a",{"class":"_3Yas"}) )
        a = a.replace('</a>', "").split('</span>') #處理完的a最後結為為...>tag
        for tag in a:
            if '>' in tag:
                tagL.append( tag.split('>')[-1] )

        # 取出文章並清除不必要html標籤
        a = str(soup.select('._1UuP p'))#找出class = _1Uup 下的p標籤
        a = a.replace( "[" ,"").replace( "]" ,"")
        n1 ,n2, rec3 = 0, 0, ""
        while n2+4<len(a):
            # 找出文章每一段落
            if n1 != 0:
                n1, n2 = a.find("<p",n2+4)+3 , a.find("</p>",n2+4)
            else:
                n1, n2 = a.find("<p")+3 , a.find("</p>")
            target = a[n1:n2]#以一組p標籤為一個段落

            # 以斷落為單位清除多餘html標籤
            # 例外處理
            for r0, r1 in reasonDict.items():
                if r0 in target:
                    target = ""
                    break

            # 正式處理
            t1, t2 = 0, 0
            repeatLong = 0#重複檢查次數
            while True:
                t1, t2 = target.find('<'), target.find('>')+1
                if t1 == -1 : break# -1代表找不到搜尋內容
                target = target.replace(target[t1:t2], "")
                repeatLong += 1
                
                if repeatLong >100:
                    rec3 = "repeatLong"
                    print(rec3)
                    #target = ""
                    break
            content.append( "".join(target) )#以每篇文章為單位, 將整理完美的段落存入content
        hrefC[keyHref] = (",".join(tagL), "".join(content).replace('"',"") )
        endC = time.time()
        rec2 = "|{}| 花費{:^5.2f}秒".format(keyHref, endC-startC)
        print(rec2)
        diary.append(rec1 + rec2 + rec3)
    driver.quit()
    return hrefC

def saveData(cleanData, tagContent):
    # 連接sqlite
    conn=sqlite3.connect('anue.sqlite3')
    sqlStr1="insert into anue values "
    for i in cleanData:
        sqlStr2 = '(NULL,"{}","{}","{}",'.format(i[0], i[1], i[2])
        sqlStr3 = '"{}","{}","{}",'.format(i[3], i[4], i[5])
        sqlStr4 = '"{}","{}")'.format(tagContent[i[4]][0], tagContent[i[4]][1])
        sqlStr = sqlStr1 +sqlStr2 + sqlStr3 + sqlStr4
        conn.execute(sqlStr)
    conn.commit()
    conn.close()

def main():
    url = 'https://news.cnyes.com/news/cat/all?exp=a'
    print('一、設定Webdriver', end = " , ")
    start = time.time()
    driver = setWebdriver()
    end = time.time()
    print("花費{:^5.2f}秒".format(end-start))
    diary.append( "一、設定Webdriver, 花費{:^5.2f}秒".format(end-start) )
    
    print('二、開啟網頁', end = " , ")
    start = time.time()
    driver = openPage(url, driver)
    end = time.time()
    print("花費{:^5.2f}秒".format(end-start))
    diary.append( "二、開啟網頁, 花費{:^5.2f}秒".format(end-start) )
    
    print('三、取得日期', end = " , ")
    yesterD = yesterDate()
    print("花費{:^5.2f}秒".format(end-start))
    
    print('四、設定資料日期', end = " , ")
    start = time.time()
    driver = makeDate(driver, yesterD)
    end = time.time()
    print("花費{:^5.2f}秒".format(end-start))
    diary.append( "四、設定目標日期, 花費{:^5.2f}秒".format(end-start) )
    
    print('五、重複捲動網頁並取得原始碼', end = " , ")
    start = time.time()
    driver, page = scrollGetHtml(driver)
    driver.quit()
    end = time.time()
    print("花費{:^5.2f}秒".format(end-start))
    diary.append( "五、重複捲動網頁並取得原始碼, 花費{:^5.2f}秒".format(end-start) )
    
    print('六、整理原始碼[YMD,HMN,classStr,title,href,classCode]')
    cleanData = tuple( pageClean(page) )
    diary.append( "六、整理原始碼[YMD,HMN,classStr,title,href,classCode]" )
    
    print('七、建立hrefc{}, key=href, value=""')
    hrefC = {i[4]:"" for i in cleanData}
    diary.append( "七、建立hrefc{}, key=href, value=''" )
    
    print('八、取得連結標籤及文章')
    diary.append('八、取得連結標籤及文章')
    start = time.time()
    tagContent = hrefTagContent(hrefC)
    end = time.time()
    print("取得連結標籤及文章共{:^5.2f}秒".format(end-start))
    diary.append( "取得連結標籤及文章共{:^5.2f}秒".format(end-start) )
    
    print('九、寫入資料庫', end = " , ")
    start = time.time()
    saveData(cleanData, tagContent)
    end = time.time()
    print("寫入資料庫共花費{:^5.2f}秒".format(end-start))
    diary.append( "九、寫入資料庫, 共花費{:^5.2f}秒".format(end-start) )
    
    

s = time.time() 
diary = [] #紀錄執行細節
yesterday = datetime.date.today() + datetime.timedelta(-1)#找出昨天的日期
fName = str(yesterday) + ".txt"
fName = fName.replace("-", "")#記錄檔yyyymmdd.txt

main()
e = time.time()
print('執行時間共{:^3d}分{:^5.2f}秒'.format(int((e-s)/60), float((e-s)%60)))
diary.append( '執行時間共{:^3.0f}分{:^5.2f}秒'.format((e-s)/60, (e-s)%60) )
with open(fName, mode='w') as f:
    f.write("\n".join(diary))
