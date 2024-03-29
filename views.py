"""This file allows to manage the web site and web page server-side"""
from celeryConfig import *
from worker import *
import glob
import time
import stat
import operator
#these values allows to insert the default labels
flag = False
count12 = 0
data = {'flag': 'true'}

#creation new Flask's components
app = Flask(__name__)
app.secret_key = 'Your_secret_string'
admin = Admin(app,"Admin Area")
admin.add_view(UserView(managedb.db.UserCollection,"User Management"))
app.config.update(
    CELERY_BROKER_URL = 'redis://localhost:6379',
    CELERY_RESULT_BACKEND = 'redis://localhost:6379'
)
celery = make_celery(app)



@app.route("/")
def index():
    """This function allows to execute the login; if user is already logged in , he will able to access the main page"""
    global data
    if "logged_in" in session and session["logged_in"] == True:
        print("User login",session["username"])
        try:
            count1 = managedb.getCountLoginDB(session["username"])
            if count1 == 0:
                session.clear()
                return render_template('loginPage.html',data=data)
            return redirect(url_for('main'))
        except Exception as e:
            print("Error DB:",str(e))
            return render_template('loginPage.html', data=data)
    return render_template('loginPage.html',data=data)

@app.route("/main")
def main():
    """This functions allows to access to web app main page"""
    global data
    if "logged_in" in session and session["logged_in"] == True:
        print("User login", session["username"])
        try:
            count1 = managedb.getCountLoginDB(session["username"])
            if count1 == 0:
                session.clear()
                return redirect(url_for('index'))
            return render_template('main.html', data=data)
        except Exception as e:
            print("Error DB:",str(e))
            return redirect(url_for('index'))
    return redirect(url_for('index'))

@app.route("/home")
def home():
    """This functions allows to access to user management page"""
    if "logged_in" in session and session["logged_in"] == True:
        print("User login", session["username"])
        try:
            count1 = managedb.getCountLoginDB(session["username"])
            if count1 == 0:
                return redirect(url_for('index'))
            return render_template('/admin/index.html')
        except Exception as e:
            print("Error DB:",str(e))
            return redirect(url_for('index'))
    return redirect(url_for('index'))

@app.route("/CSVcreation")
def CSVcreation():
    """This functions allows to access to page for the creation of csv"""
    if "logged_in" in session and session["logged_in"] == True:
        print("User login", session["username"])
        try:
            count1 = managedb.getCountLoginDB(session["username"])
            if count1 == 0:
                return redirect(url_for('index'))
            return render_template('CSVcreation.html',data=data)
        except Exception as e:
            print("Error DB:",str(e))
            return redirect(url_for('index'))
    return redirect(url_for('index'))

@app.route('/createUser',methods=["GET","POST"])
def createUser():
    """This function adds new user"""
    if "logged_in" in session and session["logged_in"] == True:
        return redirect(url_for('main'))
    if request.method == "POST":
        print("Create new user")
        name = request.form["name"]
        surname = request.form["surname"]
        username = request.form["username"]
        password = request.form["password"]
        pass_hash = generate_password_hash(password, method='pbkdf2:sha256')
        try:
            id = managedb.createUserDB(name,surname,username,pass_hash)
            session["registration"] = True
            return redirect(url_for("index"))
        except Exception as e:
            print("Error DB:",str(e))
            session["registration"] = False
            return redirect(url_for("registration"))

@app.route("/logout")
def logout():
    """This function allows to execute the logout"""
    if "logged_in" not in session or session["logged_in"] != True:
        print("Unregistered user")
    print("Logout",session["username"])
    session.clear()
    return redirect(url_for('index'))

@app.route('/login',methods=["GET","POST"])
def login():
    """This function allows to execute the login"""
    if request.method == "POST":
        print("Check login DB")
        username = request.form["username"]
        password = request.form["password"]
        print(username,password)
        try:
            count,userDB = managedb.loginDB(username)
            print(userDB)
            if(count == 0):
                session["logged_in"] = False
                print("login failed")
                return redirect(url_for('index'))
            else:
                pass_hash = userDB["password"]
                if (check_password_hash(pass_hash, password) or (password == pass_hash)):
                    session["logged_in"] = True
                    session["username"] = userDB["username"]
                    session["role"] = userDB["role"]
                    #print("Utente che accede nome:",session["username"])
                    #print("login corretto")
                    return redirect(url_for('main'))
                else:
                    session["logged_in"] = False
                    print("login failed")
                    return redirect(url_for('index'))
        except Exception as e:
            print("exception error DB11", str(e))
            return redirect(url_for('index'))

    return redirect(url_for('index'))

@app.route('/listClassPolygon',methods=["GET","POST"])
def listClassPolygon():
    """This function allows to ask db for the polygons' classes list"""
    if request.is_xhr and request.method=="POST":
        try:
            dateold = request.form['dateStr']
            datenew = datetime(int(dateold[0:4]), int(dateold[4:6]), int(dateold[6:8]), int(dateold[9:11]))
            #print("Individuare classi di Polygon con datetime : ", str(datenew))
            result, cursorListClassPolygon = managedb.groupByClassPolygonDB(datenew)
            if (result == False):
                print("Polygons' classes: there aren't results")
                return json.dumps({"result": "empty"})
            else:
                print("Polygons' classes: there are results")
                print(cursorListClassPolygon)
                cursorListClassClusterJSON = mytools.modifyClassPolygonJSON(cursorListClassPolygon)
                return cursorListClassClusterJSON
                #return json.dumps({"result": "ok"})
        except Exception as e:
            print("exception error DB", str(e))
            return json.dumps({"result": "error"})

@app.route('/insertStorm',methods=["GET","POST"])
def insertStorm():
    """This function allows to insert the polygon into db"""
    if request.is_xhr and request.method=="POST":
        #print(type(request.form))
        #for a in request.form:
        #    print("dati:",a,request.form[a])
        polygonGeoJson = request.get_json()
        #print("Polygon da inserire con datetime: ",polygonGeoJson['properties']['dateStr'])
        #modifica data in stringa in datatime
        dateold = polygonGeoJson['properties']['dateStr']
        datenew = datetime(int(dateold[0:4]),int(dateold[4:6]),int(dateold[6:8]),int(dateold[9:11]))
        polygonGeoJson['properties']['dateStr'] = datenew
        #print("data nuova:",str(polygonGeoJson['properties']['dateStr']))
        polygonGeoJson["properties"]["name"] = polygonGeoJson["properties"]["name"].upper()
        #for key, value in polygonGeoJson.iteritems():
        #    print(key,value)
        #    print(" ")
        #print(type(polygonGeoJson))

        coords = []
        for i in range(0,len(polygonGeoJson["geometry"]["coordinates"][0])):
            coords.append(tuple((polygonGeoJson["geometry"]["coordinates"][0][i][0],polygonGeoJson["geometry"]["coordinates"][0][i][1])))
        polyA = Polygon(coords)
        print(polygonGeoJson)
        print(polyA)

        count,cursorPolygon = managedb.getPolygonOnDate(datenew)
        if count > 0:
            polygons = []
            for polygon in cursorPolygon:
                coords1 = []
                for i in range(0,len(polygon["geometry"]["coordinates"][0])):
                    print("lng:",polygon["geometry"]["coordinates"][0][i][0],"lat:",polygon["geometry"]["coordinates"][0][i][1])
                    coords1.append(tuple((polygon["geometry"]["coordinates"][0][i][0],polygon["geometry"]["coordinates"][0][i][1])))
                poly = Polygon(coords1)
                polygons.append(poly)
            flag1=False
            flag2=False
            flag3=False
            flag4=False
            for i in range(0,len(polygons)):
                if(polygons[i].overlaps(polyA)):
                    flag1=True
                if (polygons[i].equals(polyA)):
                    flag2 = True
                if (polygons[i].contains(polyA)):
                    flag3 = True
                if (polygons[i].within(polyA)):
                    flag4 = True
            if flag1 or flag3 or flag4:
                return json.dumps({"result": "intersection"})
            if flag2:
                return json.dumps({"result": "alreadyinserted"})
        print(session["username"])
        try:
            count1 = managedb.getCountLoginDB(session["username"])
            if count1 == 0:
                return json.dumps({"result": "exit"})
            result,id = managedb.insertPolygonDB(polygonGeoJson)
            if result==True:
                # print("Polygon da inserire con idDB:",str(id))
                return json.dumps({"result":"correct","id":str(id)})
            else:
                return json.dumps({"result": "alreadyinserted"})
        except Exception as e:
            print("exception error DB",str(e))
            return json.dumps({"result": "error"})

@app.route('/deleteStorm',methods=["GET","POST"])
def deleteStorm():
    """This function allows to remove a polygon from db"""
    if request.is_xhr and request.method=="POST":
        idDB = request.form['id']
        print("Polygon to be deleted with idDB",idDB)
        try:
            count1 = managedb.getCountLoginDB(session["username"])
            if count1 == 0:
                return json.dumps({"result": "exit"})
            result = managedb.deletePolygonDB(idDB)
            if result == "correct":
                return json.dumps({"result":"correct"})
            elif result == "empty":
                return json.dumps({"result": "empty"})
            else:
                return json.dumps({"result": "inconsistent"})
        except Exception as e:
            print("exception error DB ",str(e))
            return json.dumps({"result" : "error"})

@app.route('/listStormOnDate',methods=["GET","POST"])
def listStormOnDate():
    """This function allows to ask the db for polygons' list of specific date"""
    if request.is_xhr and request.method=="POST":
        dateold = request.form['dateStr']
        datenew = datetime(int(dateold[0:4]), int(dateold[4:6]), int(dateold[6:8]), int(dateold[9:11]))
        print("Request Polygon list with datetime: ",str(datenew))
        try:
            result,cursorListPolygon = managedb.listPolygonOnDateDB(datenew)
            if(result == False):
                print("polygon: there aren't results")
                return json.dumps({"result": "empty"})
            else:
                print("polygon: there are results")
                cursorListPolygonJSON= mytools.modifyPolygonJSON(cursorListPolygon)
                return cursorListPolygonJSON
        except Exception as e:
            print("exception error DB",str(e))
            return json.dumps({"result":"error"})

@app.route('/listLabelsOnIdDB',methods=["GET","POST"])
def listLabelsOnIdDB():
    """This function allows to ask the db for labels' list"""
    if request.is_xhr and request.method=="POST":
        idDB = request.form["id"]
        global flag
        global count12
        try:
            count12 = managedb.countLabelDB()
            print("Label count:", count12)
            if(count12 == 0):

                flag = True
        except Exception as e:
            print("exception error DB", str(e))
            return json.dumps({"result": "error"})
        #the insertion default values
        if (flag):
            flag = False
            try:
                labels = ["","Medicane", "Storm", "Thunderstorm"]
                for l in labels:
                    label = {"labelName": l.upper(),"labelId":count12}
                    result15,id = managedb.insertLabelDB(label)
                    #print(result15,id)
                    if(result15 == True):
                        print("Label id:", str(id))
                        count12 += 1
                    else:
                        print("Label already inserted")
            except Exception as e:
                print("exception error DB", str(e))
                return json.dumps({"result": "error"})
        try:
            result,cursorListLabel = managedb.listLabelDB()
            if(result == False):
                print("label: there aren't results")
                return json.dumps({"result": "empty"})
            else:
                print("label: there are results")
                cursorListLabelJSON = mytools.modifyLabelJSON(cursorListLabel)
                return cursorListLabelJSON
        except Exception as e:
            print("exception error DB",str(e))
            return json.dumps({"result":"error"})

@app.route('/insertLabelsOnIdDB',methods=["GET","POST"])
def insertLabelsOnIdDB():
    """This function allows to add a new label"""
    global count12
    if request.is_xhr and request.method=="POST":
        try:
            count1 = managedb.getCountLoginDB(session["username"])
            if count1 == 0:
                return json.dumps({"result": "exit"})
            count12 = managedb.countLabelDB()
        except Exception as e:
            print("exception error DB", str(e))
        l = request.form["label"]
        label = {"labelName":l.upper(),"labelId":count12}
        print("Label da inserire,",l.upper(), "labelId",count12)
        try:
            result,id = managedb.insertLabelDB(label)
            if result == True:
                print("label id:", str(id))
                count12 += 1
                return json.dumps({"result": "correct"})
            else:
                return json.dumps({"result": "alreadyinserted"})
        except Exception as e:
            print("exception error DB", str(e))
            return json.dumps({"result": "error"})

@app.route('/countPolygon',methods=["GET","POST"])
def countPolygon():
    if request.is_xhr and request.method=="POST":
        dateold = request.form["dateStr"]
        print(dateold)
        datenew = datetime(int(dateold[0:4]), int(dateold[4:6]), int(dateold[6:8]), int(dateold[9:11]))
        try:
            count = managedb.countPolygonDB(datenew)
            return json.dumps({"result": "correct","count": str(count)})
        except Exception as e:
            print("exception error DB",str(e))
            return json.dumps({"result": "error"})

@app.route('/checkLabel',methods=["GET","POST"])
def checkLabel():
    """This function allows to change the label of a polygon"""
    if request.is_xhr and request.method=="POST":
        idDB = request.form["id"]
        #print("modifica label del Polygon con idDB",idDB)
        #print("nuova etichetta",name)
        try:
            count,result1,cursorPolygon = managedb.checkLabelPolygononIdDB(idDB)
            if(count == 1):
                result2 = {"result":"correct","label":cursorPolygon["properties"]["name"]}
                print result2
                return result2
            elif(count == 0):
                return json.dumps({"result": "empty"})
            else:
                return json.dumps({"result": "inconsistent"})
        except Exception as e:
            print("exception error DB",str(e))
            return json.dumps({"result": "error"})


@app.route('/modifyLabel',methods=["GET","POST"])
def modifyLabel():
    """This function allows to change the label of a polygon"""
    if request.is_xhr and request.method=="POST":
        idDB = request.form["id"]
        name = request.form["name"]
        #print("modifica label del Polygon con idDB",idDB)
        #print("nuova etichetta",name)
        try:
            count1 = managedb.getCountLoginDB(session["username"])
            if count1 == 0:
                return json.dumps({"result": "exit"})
            managedb.modifyLabelPolygonOnIdDB(idDB,name)
            return json.dumps({"result": "correct"})
        except Exception as e:
            print("exception error DB",str(e))
            return json.dumps({"result": "error"})

@app.route('/listPointClusterOnDate',methods=["GET","POST"])
def listPointClusterOnDate():
    """This function asks the db for clusters' points list of specific date"""
    if request.is_xhr and request.method=="POST":
        dateold = request.form['dateStr']
        datenew = datetime(int(dateold[0:4]), int(dateold[4:6]), int(dateold[6:8]), int(dateold[9:11]))
        #print("Individuare i Point Cluster con datetime", str(datenew))
        try:
            result, cursorListPointCluster = managedb.listPointClusterOnDateDB(datenew)
            if (result == False):
                print("point: there aren't results")
                return json.dumps({"result": "empty"})
            else:
                print("point: there are results")
                cursorListPointClusterJSON = mytools.modifyPointClusterJSON(cursorListPointCluster)
                return cursorListPointClusterJSON
        except Exception as e:
            print("exception error DB", str(e))
            return json.dumps({"result": "error"})

@app.route('/listClassCluster',methods=["GET","POST"])
def listClassCluster():
    """This function asks the db for clusters' classes list"""
    if request.is_xhr and request.method=="POST":
        try:
            result, cursorListClassCluster = managedb.listClassClusterDB()
            if (result == False):
                print("clusters' classes: there aren't results")
                return json.dumps({"result": "empty"})
            else:
                print("clusters' classes: there are results")
                cursorListClassClusterJSON = mytools.modifyClassClusterJSON(cursorListClassCluster)
                return cursorListClassClusterJSON
        except Exception as e:
            print("exception error DB", str(e))
            return json.dumps({"result": "error"})

@app.route('/csvCreationRequest',methods=["GET","POST"])
def csvCreationRequest(): #rStart,rEnd,yStart,mStart,dStart,hStart,yEnd,mEnd,dEnd,hEnd
    """This method allows to generate csv file of netCDF"""
    if request.is_xhr and request.method=="POST":
        startDate = request.form["startDate"]
        startDate = startDate.split("-")
        yStart = startDate[0]
        mStart = startDate[1]
        dStart = startDate[2]
        hStart = request.form["startHour"]
        endDate = request.form["endDate"]
        endDate = endDate.split("-")
        yEnd = endDate[0]
        mEnd = endDate[1]
        dEnd = endDate[2]
        hEnd = request.form["endHour"]
        rStart =request.form["rStart"]
        rEnd = request.form["rEnd"]
        print(rStart,rEnd,yStart,mStart,dStart,hStart,yEnd,mEnd,dEnd,hEnd)
        result = pointInPolygon(session["username"],int(rStart),int(rEnd),int(yStart),int(mStart),int(dStart),int(hStart),int(yEnd), int(mEnd), int(dEnd), int(hEnd))
        countTot = result
        if countTot == -1:
            return json.dumps({"result": "error"})
        if countTot == None:
            return json.dumps({"result": "error1"})
        if countTot == 0:
            return json.dumps({"result": "nofiles","count":str(countTot)})
        else:
            return json.dumps({"result": "files","count":str(countTot)})

@app.route('/getFileCSV',methods=["GET","POST"])
def getFileCSV():
    """This function asks the db for clusters' classes list"""
    if request.is_xhr and request.method=="POST":
        username = request.form["username"]
        print(username)
        pathname = "static/user_files/"+username+"/*.csv"
        files = sorted(glob.glob(pathname), key=os.path.getmtime)
        files1 = []
        info1 = []
        for i in range(0,len(files)):
            pre, ext = os.path.splitext(os.path.basename(urlparse.urlsplit(files[i]).path))
            print(files[i])
            file_stats = os.stat(files[i])
            #print(file_stats)
            f_ct = time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(file_stats[stat.ST_CTIME]))
            print(f_ct)
            file = pre+ext
            print(file)
            file_info ={"filename":file,"f_ct":f_ct}
            files1.append(file_info)
        print(files1)
        #files1.sort(key=operator.itemgetter("f_ct"))
        #print(files1)
        return json.dumps({"result": files1})

@app.route('/deleteFileCSV',methods=["GET","POST"])
def deleteFileCSV():
    if request.is_xhr and request.method=="POST":
        path1 = request.form["path"]
        print(path1)
        try:
            if os.path.exists(path1):
                os.remove(path1)
                print("removed")
                return json.dumps({"result": "removed"})
            else:
                print("The file does not exist")
                return json.dumps({"result": "doesnotexist"})
        except Exception as e:
            print("Error File:", str(e))
            json.dumps({"result": "problemFile"})

@celery.task()
def wrapWorkerUrl(username,url):
    result = workerUrl(username, url)
    return result

@celery.task()
def wrapWorkerNcFile(username,ncfile):
    result = workerNcfile(username, ncfile)
    return result

def pointInPolygon(username, rStart, rEnd, yStart, mStart, dStart, hStart, yEnd, mEnd, dEnd, hEnd):
    print("Process start")
    print(rStart, rEnd, yStart, mStart, dStart, hStart, yEnd, mEnd, dEnd, hEnd)
    try:
            mytool = MyTools()
            managedb = ManageDB()
            if mytool.validityCheckDB(managedb):

                # resolution, start date, end date
                ncfiles, urls = mytool.getUrls(rStart, rEnd, yStart, mStart, dStart, hStart, yEnd, mEnd, dEnd, hEnd)
                print("------------------------------------------------------------------------------------")
                print("number of file in local storage:", len(ncfiles), "number of file in internet:", len(urls))
                # p = multiprocessing.Pool(processes=nThreads)
                print("------------------------------------------------------------------------------------")
                print("Start scan files online")
                # p.map(workerUrls, urls)
                for i in range(0, len(urls)):
                    result = wrapWorkerUrl.delay(username, urls[i])
                    print("celery workerUrl",result.wait())
                print("------------------------------------------------------------------------------------")
                print("Start scan files in local storage")
                # The software divides the analysis of netCDF files amoung threads
                # p.map(workerNcfile, ncfiles)
                for i in range(0, len(ncfiles)):
                    result = wrapWorkerNcFile.delay(username, ncfiles[i])
                    print("celery workerNcFile",result.wait())
                countFiles = len(ncfiles) + len(urls)
                return countFiles
            countFiles = None
            return countFiles
    except Exception as e:
            print("Error DB or File:", str(e))
            countFiles = -1
            return countFiles
