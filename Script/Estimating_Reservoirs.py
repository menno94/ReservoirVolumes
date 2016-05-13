# -*- coding: utf-8 -*-
"""
Created on Sun May 24 2015

Created by      C.W.T. van Bemmelen
                M. Mann
                M.P. de Ridder
                
cwtvanbemmelen@tudelft.nl
mmann@tudelft.nl
mpderidder@tudelft.nl

This script is used for estimating large reservoir volumes.
Running this script is done in GRASS 7.0.0. or higher.
A DEM projected in UTM is needed.
Results are stored in CSV files.

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

# 1a.Input DEM (UTM) & Reservoir to be estimated
path_to_DEM = r"Specify the path to your DEM here" 
Reservoir_name = "XX"

# 1a. Fill in reference area [m2] and starting water height [m]
ref_area = VARIABLE  
WH = VARIABLE       #Large number is suggested    

# 1b. Input virtual Dams (X1..Xn - Y1..Yn)                                             
X_coordinateDAM = []
Y_coordinateDAM = []

# 1b. Append to xy list
xy = []                            
for i in range(len(X_coordinateDAM)):
    xy.append(str(X_coordinateDAM[i]) + "," + str(Y_coordinateDAM[i]))

# 1c. Input destination CSV-file
g=open(r"#Specify the path and name.csv",'wb')
writer=csv.writer(g,delimiter=',',quotechar='"',quoting=csv.QUOTE_MINIMAL)

# 2a.GRASS -> open the DEM in GRASS
DEM = grass.run_command("r.in.gdal",input=path_to_DEM,output="DEM",overwrite=True)

# 2b.GRASS -> set region
region = grass.run_command("g.region",flags="d",rast="DEM",overwrite=True)

# 3.Write metadata for csv
nsres = grass.raster_info('DEM')['nsres']
ewres = grass.raster_info('DEM')['ewres']
writer.writerow(["Estimating reservoir:",Reservoir_name])
writer.writerow(["Resolution (Nsres/ewres)",nsres,ewres])
writer.writerow(["Dam Locations (X1,Y1..Xn,Yn):",xy])
writer.writerow(["Waterlevel","Volume","Area"])

# 4.GRASS -> create drainage direction map and drainage accumulation map
drain_dir_acc = grass.run_command("r.watershed",elevation="DEM",drainage="drain_dir",accumulation="drain_acc",overwrite=True)
for i in range(len(X_coordinateDAM)):
    # 5. Get coordinates corresponding to DEM (instead of coordinates of the dam)
    circle = grass.run_command("r.circle",flags="b",coordinate=xy[i],min=0,max=VARIABLE,output="circle",overwrite=True)
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
    
    # 7a. Create sub-basin for virtual Dam
    sub_basin = grass.run_command("r.water.outlet",input="drain_dir",output="sub_basin",coordinates=(x,y),overwrite=True)
    
    # 7b. Create walls around the sub-basin
    grass.mapcalc("$sub_basin_walls = if(isnull($sub_basin),$value,$DEM,$DEM)",sub_basin_walls = "sub_basin_walls", sub_basin = "sub_basin", DEM = "DEM",value = 9999, overwrite=True)
    
    # 8. Create necessary variables to store results
    volume = []
    area = []
    
    # 9. Determine first large reservoir water level
    waterlevel = int(DEM_height)+WH
    
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

print "Done estimating large reservoir area volume relationship."

