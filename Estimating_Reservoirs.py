# -*- coding: utf-8 -*-
"""
Created on Sun May 24 2015

Created by      C.W.T. van Bemmelen
                M. Mann
                M.P. de Ridder
                
casvbem@gmail.com
"""

###############################################
###         1.START GRASS SESSION           ###
###############################################

import grass.script as grass
import grass.script.setup as gsetup

##############Important imports##############
import csv
import StringIO
import string
import numpy as np
##############Important imports##############

# 1a.Input & Reservoir to be estimated
path_to_DEM = r"C:\Users\Cas\Documents\grassdata\DEMUTM18.tif" 
Reservoir_name = "Tridelphia"
# 1a. Fill in reference area
ref_area = 6300*400               

# 1b. Input virtual Dams (X1..Xn - Y1..Yn)                                             
X_coordinateDAM = [322968.591189,316664.509151,326153.397707,316376.172758,308715.599055]
Y_coordinateDAM = [14347282.5277,14348671.7849,14338291.6748,14330252.6596,14324839.7991]

# 1b. Append to xy list
xy = []                            
for i in range(len(X_coordinateDAM)):
    xy.append(str(X_coordinateDAM[i]) + "," + str(Y_coordinateDAM[i]))

# 1c. Input destination CSV-file
g=open(r"C:\Users\Cas\Documents\Volumes\Tridelphia_ACcurve_test3.csv",'wb')
writer=csv.writer(g,delimiter=',',quotechar='"',quoting=csv.QUOTE_MINIMAL)

# 2a.Open the DEM in GRASS
DEM = grass.run_command("r.in.gdal",input=path_to_DEM,output="DEM",overwrite=True)

# 2b.Set region
region = grass.run_command("g.region",flags="d",rast="DEM",overwrite=True)

# 3.Write metadata
nsres = grass.raster_info('DEM')['nsres']
ewres = grass.raster_info('DEM')['ewres']
writer.writerow(["Estimating reservoir:",Reservoir_name])
writer.writerow(["Resolution (Nsres/ewres)",nsres,ewres])
writer.writerow(["Dam Locations (X1,Y1..Xn,Yn):",xy])
writer.writerow(["Waterlevel","Volume","Area"])

# 4.Create drainage direction map and drainage accumulation map
drain_dir_acc = grass.run_command("r.watershed",elevation="DEM",drainage="drain_dir",accumulation="drain_acc",overwrite=True)
for i in range(len(X_coordinateDAM)):
    # 5. Get coordinates corresponding to DEM (instead of coordinates of the dam)
    circle = grass.run_command("r.circle",flags="b",coordinate=xy[i],min=0,max=250,output="circle",overwrite=True)
    grass.mapcalc("$inter1=abs(if(isnull($circle),null(),drain_acc,drain_acc))",inter1="inter1",circle="circle",drain_acc="drain_acc",overwrite=True)
    univar = grass.read_command('r.info', map='inter1',flags="r")
    maximum = float(univar.split('\n')[1].split('=')[1])
    grass.mapcalc("$inter2=if($inter1>$maximum-0.1,1,null())",inter2="inter2",inter1="inter1",maximum=maximum,overwrite=True)
    x_y = grass.read_command("r.out.xyz",input="inter2", output="-",separator = ",")
    x_y = x_y[:-3]
    x = float(x_y.split('\n')[0].split(',')[0])
    y = float(x_y.split('\n')[0].split(',')[1])
    
    # 6. Height of DEM on Dam Location
    what = grass.read_command("r.what",map='DEM',flags="i", coordinates=(x,y))
    W_values=string.split(what,'|')
    DEM_height = W_values[3]
    print DEM_height
    
    # 7a. Create sub-basin for Dam
    sub_basin = grass.run_command("r.water.outlet",input="drain_dir",output="sub_basin",coordinates=(x,y),overwrite=True)
    
    # 7b. Create walls around the sub-basin
    grass.mapcalc("$sub_basin_walls = if(isnull($sub_basin),$value,$DEM,$DEM)",sub_basin_walls = "sub_basin_walls", sub_basin = "sub_basin", DEM = "DEM",value = 9999, overwrite=True)
    
    # 8. Create necessary variables to store results
    volume = []
    area = []
    
    # 9. Determine first large reservoir water level
    waterlevel = int(DEM_height)+40 #choose a level well above the DEM value at the location of the dam
    
    # 10. Create lake map at maximum waterlevel
    lake = grass.run_command("r.lake",elevation="sub_basin_walls",water_level=waterlevel,lake="lake",coordinates=x_y,overwrite=True)
    depth = grass.read_command("r.out.xyz",input="lake",separator=',')
    depth_array=[]
    
    # 11. Deplete the lake by one meter at a time and store new volume and area in csv file
    f = StringIO.StringIO(depth)
    reader = csv.reader(f, delimiter=',')
    for row in reader:
        depth_array.append(int(row[2].split(',')[0]))
        
    depths = np.array(depth_array)
    
    for depletion in range(0,max(depths)):
        volume = sum(depths*nsres*ewres)
        area = nsres*ewres*len(depths)
        if 0.2*ref_area <= area <= 1.5*ref_area: #Area constraint 0.2-1.5
            writer.writerow([waterlevel,volume,area])
        depths = depths-1
        depths = np.delete(depths, np.where((depths == 0 )))
        waterlevel = waterlevel-1
    #writer.writerow(["NEW RESERVOIR"])
g.close()

print "Done"
