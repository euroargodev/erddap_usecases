# Argo ERDDAP Use Cases

In this repo, we'll show some use cases of the Argo data ERDDAP API hosted by Ifremer:  
http://www.ifremer.fr/erddap/tabledap/ArgoFloats.html

http://www.ifremer.fr/erddap

## Ifremer ERDDAP basic

List of datasets: http://www.ifremer.fr/erddap/tabledap/index.html

Argo data ID: ArgoFloats

## Ifremer ERDDAP examples

### For one or more floats

Positions:
http://www.ifremer.fr/erddap/tabledap/ArgoFloats.graph?longitude,latitude,cycle_number&platform_number=~%22%5E(6902746%7C6902757%7C6902766%7C6902771%7C6902772)%22&longitude%3E=-75&longitude%3C=-45&latitude%3E=15&latitude%3C=45&.draw=markers&.marker=7%7C3&.color=0x000000&.colorBar=%7C%7C%7C0%7C20%7C10&.bgColor=0xffccccff

Upper temperature profiles:
http://www.ifremer.fr/erddap/tabledap/ArgoFloats.largePng?temp%2Cpres%2Ctime&platform_number=~%22%5E(6902746%7C6902757%7C6902766%7C6902771%7C6902772)%22&.draw=markers&.marker=7%7C5&.color=0xFFFFFF&.colorBar=%7C%7C%7C%7C%7C&.xRange=16%7C30%7Ctrue&.yRange=250%7C0%7Cfalse&.bgColor=0xffffff

1 float all data:
http://www.ifremer.fr/erddap/tabledap/ArgoFloats.htmlTable?&platform_number=%226902636%22

### Space and/or time selection
Active Coriolis Floats since a given date:
http://www.ifremer.fr/erddap/tabledap/ArgoFloats.htmlTable?data_center,project_name,pi_name,platform_number&data_center=%22IF%22&time%3E=%222017-03-01T12:00:00Z%22&pres%3C=10&pres%3E=9&distinct()&orderBy(%22project_name%22)

1 day of floats:
http://www.ifremer.fr/erddap/tabledap/ArgoFloats.htmlTable?time,longitude%2Clatitude,platform_number%2Ccycle_number&time%3E=2017-06-27T00%3A00%3A00Z&time%3C=2017-06-27T23%3A59%3A59Z&pres%3E=25&pres%3C=50&distinct()&orderBy(%22time%22)&.draw=markers&.marker=5%7C5&.color=0x000000&.colorBar=%7C%7C%7C%7C%7C&.bgColor=0xffccccff

1 float cycle temperature profile:
http://www.ifremer.fr/erddap/tabledap/ArgoFloats.graph?temp%2Cpres%2Cpsal%2Ccycle_number&platform_number=%226902766%22&cycle_number%3E=9&direction=%22A%22&distinct()&orderBy(%22cycle_number%22)&.draw=markers&.marker=3%7C5&.color=0xFFFFFF&.colorBar=Rainbow2%7CD%7C%7C34%7C37%7C&.yRange=0%7C2000%7Cfalse&.bgColor=fff

1 float temperature section:
http://www.ifremer.fr/erddap/tabledap/ArgoFloats.graph?time%2Cpres%2Ctemp%2Ccycle_number&platform_number=%226902766%22&direction=%22A%22&distinct()&orderBy(%22cycle_number%22)&.draw=markers&.marker=6%7C5&.color=0xFFFFFF&.colorBar=Rainbow2%7CD%7C%7C%7C%7C&.yRange=0%7C2000%7Cfalse&.bgColor=0x7fffffff

Deployment position of ALL Argo floats:
http://www.ifremer.fr/erddap/tabledap/ArgoFloats.csv?longitude,latitude,time,project_name&cycle_number=1

Deployment position of ALL Argo floats after a given date:
http://www.ifremer.fr/erddap/tabledap/ArgoFloats.csv?longitude,latitude,time,project_name&cycle_number=1&time>="2016-03-14T12:00:00Z"

http://www.ifremer.fr/erddap/tabledap/ArgoFloats.png?longitude,latitude,pres&time%3E=2017-01-01T00:00:00Z&temp%3E=17&temp%3C=19&latitude%3E=20&latitude%3C=50&longitude%3E=-90&longitude%3C=0

### More advance usage

All argo data with temperature between 17 and 19 degC:
http://www.ifremer.fr/erddap/tabledap/ArgoFloats.htmlTable?&temp%3E=17&temp%3C=19

List of positions of 1 float data with temperature between 17 and 19 degC:
http://www.ifremer.fr/erddap/tabledap/ArgoFloats.htmlTable?longitude%2Clatitude%2Ctime&platform_number=%226902636%22&temp%3E=17&temp%3C=19&orderBy(%22time%22)

Figure with positions of 1 float data with temperature between 17 and 19 degC:
(simply replace .htmlTable by .graph)
http://www.ifremer.fr/erddap/tabledap/ArgoFloats.htmlTable?longitude%2Clatitude%2Ctime&platform_number=%226902636%22&temp%3E=17&temp%3C=19&orderBy(%22time%22)

Depth (pressure) of the 17-19degC layer since Jan. 2017:
http://www.ifremer.fr/erddap/tabledap/ArgoFloats.largePng?longitude%2Clatitude%2Cpres&pres%3E=300&time%3E=2017-01-01T00%3A00%3A00Z&temp%3E=17&temp%3C=19&latitude%3E=10&latitude%3C=50&longitude%3E=-90&longitude%3C=0&distinct()&.draw=markers&.marker=7%7C3&.color=0x000000&.colorBar=ReverseRainbow%7CD%7C%7C300%7C600%7C&.bgColor=0xffccccff

Depth (pressure) of the 17-19degC layer for last winter:
http://www.ifremer.fr/erddap/tabledap/ArgoFloats.graph?longitude%2Clatitude%2Cpres&pres%3E=250&temp%3E=17&temp%3C=19&psal%3E=36.4&psal%3C=36.6&latitude%3E=20&latitude%3C=45&longitude%3E=-81&longitude%3C=-40&time%3E=2016-12-01T00%3A00%3A00Z&time%3C=2017-03-31T00%3A00%3A00Z&distinct()&.draw=markers&.marker=7%7C6&.color=0x000000&.colorBar=ReverseRainbow%7CD%7C%7C300%7C600%7C&.bgColor=0xffccccff

EDW outcropping area temperature time series:
http://www.ifremer.fr/erddap/tabledap/ArgoFloats.graph?time%2Ctemp%2Cpsal&time%3E=2015-09-01T00%3A00%3A00Z&longitude%3E=-60&longitude%3C=-50&latitude%3E=32.5&latitude%3C=37.5&pres%3E=40&pres%3C=60&temp%3E=15&.draw=markers&.marker=5%7C5&.color=0x000000&.colorBar=%7C%7C%7C36.3%7C36.7%7C&.bgColor=0xffccccff