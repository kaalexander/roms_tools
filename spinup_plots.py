from netCDF4 import Dataset
from numpy import *
from matplotlib.pyplot import *
from os.path import *
from cartesian_grid_3d import *

# Analyse a ROMS spinup by calculating and plotting 10 timeseries:
# Total heat content
# Total salt content
# Area-averaged ice shelf melt rate
# Ice shelf basal mass loss
# Total kinetic energy
# Maximum velocity
# Drake Passage transport
# Total sea ice extent
# Net sea ice-to-ocean freshwater flux
# Area-averaged bottom water temperature in ice shelf cavities


# Given the path to a ROMS grid file, calculate differentials for later
# integration.
# Input: file_path = string containing path to ROMS history/averages file
# Output:
# dA = differential of area on the 2D rho-grid, masked with zice
# dV = differential of volume on the 3D rho-grid (depth x lat x lon), masked
#      with land mask
# dy_wct = differential of y times water column thickness for each cell on the 
#          2D rho-grid, masked with land mask
def calc_grid (file_path):

    # Grid parameters
    theta_s = 0.9
    theta_b = 4.0
    hc = 40
    N = 31

    # Read grid variables
    id = Dataset(file_path, 'r')
    h = id.variables['h'][:,:]
    zice = id.variables['zice'][:,:]
    lon = id.variables['lon_rho'][:,:]
    lat = id.variables['lat_rho'][:,:]
    mask = id.variables['mask_rho'][:,:]
    id.close()

    # Calculate water column thickness
    wct = h + zice

    # Calculate Cartesian integrands and z-coordinates
    dx, dy, dz, z = cartesian_grid_3d(lon, lat, h, zice, theta_s, theta_b, hc, N)

    # Calculate dA (2D) and mask with zice
    dA = ma.masked_where(zice==0, dx[0,:,:]*dy[0,:,:])
    
    # Calculate dV and mask with land mask
    mask_3d = tile(mask, (N,1,1))
    dV = ma.masked_where(mask_3d==0, dx*dy*dz)
    # Similarly for dy_wct (2D)
    dy_wct = ma.masked_where(mask==0, dy[0,:,:]*wct)

    return dA, dV, dy_wct


# Read and return density.
# Input:
# file_path = path to ocean history/averages file
# t = timestep index in file_path
# Output: rho = density field at timestep t
def get_rho (file_path, t):

    # Reference density
    rho0 = 1000.0

    id = Dataset(file_path, 'r')
    # Read density anomalies, add rho0 to get absolute density
    # Convert to float128 to prevent overflow later
    rho = ma.asarray(id.variables['rho'][t,:,:,:], dtype=float128) + rho0
    id.close()
    return rho


# Calculate ocean heat content at the given timestep t.
# Input:
# file_path = path to ocean history/averages file
# dV = elements of volume on the rho grid, masked with land mask
# rho = density on the rho grid at timestep t
# t = timestep index in file_path
# Output: ohc = ocean heat content (J)
def calc_ohc (file_path, dV, rho, t):

    # Specific heat of polar seawater (J/K/kg)
    cp = 3974.0
    # Celsius to Kelvin conversion constant
    celsius2kelvin = 273.15

    # Read temperature, converting to float128 to prevent overflow during
    # integration
    id = Dataset(file_path, 'r')
    temp = ma.asarray(id.variables['temp'][t,:,:,:], dtype=float128)
    # Convert from Celsius to Kelvin
    temp = temp + celsius2kelvin
    id.close()

    # Integrate temp*rho*cp over volume to get OHC
    ohc = sum(temp*rho*cp*dV)
    return ohc


# Calculate total salt content at the given timestep t.
# Input:
# file_path = path to ocean history/averages file
# dV = elements of volume on the rho grid, masked with land mask
# rho = density on the rho grid at timestep t
# t = timestep index in file_path
# Output: totalsalt = total salt content (kg)
def calc_totalsalt (file_path, dV, rho, t):

    # Read salinity, converting to float128 to prevent overflow during
    # integration
    id = Dataset(file_path, 'r')
    salt = ma.asarray(id.variables['salt'][t,:,:,:], dtype=float128)
    id.close()

    # Integrate 1e-3*salt*rho over volume to get total mass of salt
    totalsalt = sum(1e-3*salt*rho*dV)
    return totalsalt    


# Calculate area-averaged ice shelf melt rate at the given timestep t.
# Input:
# file_path = path to ocean history/averages file
# dA = elements of area on the rho grid, masked with zice
# t = timestep index in file_path
# Output: avgismr = area-averaged ice shelf melt rate (m/y)
#         ismr = 2D ice shelf melt rate field (m/y) at this timestep
def calc_avgismr (file_path, dA, t):

    # Read ice shelf melt rate, converting to float128 to prevent overflow
    # during integration
    id = Dataset(file_path, 'r')
    ismr = ma.asarray(id.variables['m'][t,:,:], dtype=float128)
    # Convert from m/s to m/y
    ismr = ismr*365.25*24*60*60
    id.close()    

    # Integrate ismr over area and divide by total area to get average
    avgismr = sum(ismr*dA)/sum(dA)
    return avgismr, ismr


# Calculate net basal mass loss based on the given ice shelf melt rate field.
# Input:
# ismr = 2D ice shelf melt rate field (m/y)
# dA = elements of area on the rho grid, masked with zice
# Output: massloss = net basal mass loss (Gt/y)
def calc_massloss (ismr, dA):

    # Density of ice in kg/m^3
    rho_ice = 916

    # Integrate over area to get volume loss
    volumeloss = sum(ismr*dA)
    # Convert to mass loss in Gt/y
    massloss = 1e-12*rho_ice*volumeloss
    return massloss


# Calculate total kinetic energy at the given timestep t.
# Input:
# file_path = path to ocean history/averages file
# dV = elements of volume on the rho grid, masked with land mask
# rho = density on the rho grid at timestep t
# t = timestep index in file_path
# Output: tke = total kinetic energy (J)
def calc_tke (file_path, dV, rho, t):

    # Read u and v, converting to float 128 to prevent overflow during
    # integration
    id = Dataset(file_path, 'r')
    u = ma.asarray(id.variables['u'][t,:,:,:], dtype=float128)
    v = ma.asarray(id.variables['v'][t,:,:,:], dtype=float128)
    id.close()

    # Interpolate u onto the rho-grid
    w_bdry_u = 0.5*(u[:,:,0] + u[:,:,-1])
    middle_u = 0.5*(u[:,:,0:-1] + u[:,:,1:])
    e_bdry_u = w_bdry_u[:,:]
    u_rho = ma.concatenate((w_bdry_u[:,:,None], middle_u, e_bdry_u[:,:,None]), axis=2)

    # Interpolate v onto the rho-grid
    s_bdry_v = v[:,0,:]
    middle_v = 0.5*(v[:,0:-1,:] + v[:,1:,:])
    n_bdry_v = v[:,-1,:]
    v_rho = ma.concatenate((s_bdry_v[:,None,:], middle_v, n_bdry_v[:,None,:]), axis=1)

    # Integrate 0.5*rho*(u^2 + v^2) over volume to get TKE
    tke = sum(0.5*rho*(u_rho**2 + v_rho**2)*dV)
    return tke, u_rho, v_rho


# Calculate the maximum velocity.
# Input: u_rho, v_rho = u and v at timestep t, interpolated to the rho-grid
# Output: maxvel = maximum velocity (m/s)
def calc_maxvel (u_rho, v_rho):

    return amax(sqrt(u_rho**2 + v_rho**2))


# Calculate zonal transport through the Drake Passage.
# Input:
# file_path = path to ocean history/averages file
# dy_wct = differential of y times water column thickness for each cell on the 
#          2D rho-grid, masked with land mask
# t = timestep index in file_path
# Output: drakepsg_trans = zonal transport through the Drake Passage (60W),
#                          integrated over depth and latitude
def calc_drakepsgtrans (file_path, dy_wct, t):

    # Bounds on Drake Passage; edit for new grids
    # i-index of single north-south line to plot (representing a zonal slice);
    # it doesn't really matter which slice of the Drake Passage this is, due
    # to volume conservation
    i_DP = 1179
    # j-indices of the southern tip of South America (j_min) and the northern
    # tip of the Antarctic Peninsula (j_max); make sure these are far enough
    # north/south to be land points, but not so far that they pass through the
    # land and become ocean again (eg Weddell Sea)
    j_min = 229
    j_max = 298

    # Read ubar, converting to float128 to prevent overflow during integration
    id = Dataset(file_path, 'r')
    ubar = ma.asarray(id.variables['ubar'][t,:,:], dtype=float128)
    id.close()

    # Interpolate ubar onto the rho-grid
    w_bdry_ubar = 0.5*(ubar[:,0] + ubar[:,-1])
    middle_ubar = 0.5*(ubar[:,0:-1] + ubar[:,1:])
    e_bdry_ubar = w_bdry_ubar[:]
    ubar_rho = ma.concatenate((w_bdry_ubar[:,None], middle_ubar, e_bdry_ubar[:,None]), axis=1)

    # Trim arrays to these bounds
    ubar_rho_DP = ubar_rho[j_min:j_max,i_DP]
    dy_wct_DP = dy_wct[j_min:j_max,i_DP]

    # Calculate transport
    transport = sum(ubar_rho_DP*dy_wct_DP)

    # Divide by 1e6 to convert to Sv
    return transport*1e-6


# Calculate total sea ice extent at the given timestep t.
# Input:
# cice_path = path to CICE history file
# dA = elements of area on the 2D rho grid (any mask will be removed)
# t = timestep index in cice_path
# Output: totalice = total sea ice extent (m^2)
def calc_totalice (cice_path, dA, t):

    id = Dataset(cice_path, 'r')
    # Read sea ice area fraction at each grid cell
    aice = ma.asarray(id.variables['aice'][t,:,:], dtype=float128)
    id.close()

    # Remove masks on aice and dA, and fill aice with zeros on land mask
    # (numpy was throwing weird masking errors originally, and it doesn't
    # matter if dA is unmasked because we are integrating not averaging)
    aice_nomask = aice.data
    aice_nomask[aice.mask] = 0.0
    dA_nomask = dA.data

    # Find the cells with at least 15% sea ice
    extent_flag = aice_nomask >= 0.15

    # Integrate area of these cells
    totalice = sum(dA_nomask*extent_flag)
    # Convert to million km^2 and return
    return totalice*1e-12   


# Calculate total sea ice-to-ocean freshwater flux at the given timestep t.
# Input:
# cice_path = path to CICE history file
# dA = elements of area on the 2D rho grid (any mask will be removed)
# t = timestep index in cice_path
# Output: fwflux = total sea ice-to-ocean freshwater flux (Sv)
def calc_totalfwflux (cice_path, dA, t):

    id = Dataset(cice_path, 'r')
    # Read freshwater and salt fluxes at each grid cell
    fresh = ma.asarray(id.variables['fresh_ai'][t,:,:], dtype=float128)/100./24./60./60
    fsalt = ma.asarray(id.variables['fsalt_ai'][t,:,:], dtype=float128)/1000.
    fwflux = fresh - fsalt    
    id.close()

    # Remove masks on net_fwflux and dA, and fill aice with zeros on land mask
    # (numpy was throwing weird masking errors originally, and it doesn't
    # matter if dA is unmasked because we are integrating not averaging)
    fwflux_nomask = fwflux.data
    fwflux_nomask[fwflux.mask] = 0.0
    dA_nomask = dA.data

    # Integrate
    total_fwflux = sum(fwflux_nomask*dA_nomask)
    # Convert to Sv and return
    return total_fwflux*1e-6


# Calculate area-averaged bottom water temperature in ice shelf cavities at the
# given timestep t.
# Input:
# file_path = path to ROMS ocean history or averages file
# dA = elements of area on the 2D rho grid, masked with zice
# t = timestep index in file_path
# Output: bwtemp = average bottom water temperature in ice shelf cavities (C)
def calc_bwtemp (file_path, dA, t):

    id = Dataset(file_path, 'r')
    temp = ma.asarray(id.variables['temp'][t,0,:,:], dtype=float128)
    zice = id.variables['zice'][:,:]
    id.close()

    cavity_temp = ma.masked_where(zice==0, temp)

    bwtemp = sum(cavity_temp*dA)/sum(dA)
    return bwtemp


# Main routine
# Input:
# file_path = path to ocean history/averages file
# cice_path = path to CICE history file
# log_path = path to log file (if it exists, previously calculated values will
#            be read from it; regardless, it will be overwritten with all
#            calculated values following computation)
def spinup_plots (file_path, cice_path, log_path):

    time = []
    #ohc = []
    #totalsalt = []
    avgismr = []
    massloss = []
    #tke = []
    #maxvel = []
    drakepsgtrans = []
    totalice = []
    totalfwflux = []
    bwtemp = []
    # Check if the log file exists
    if exists(log_path):
        print 'Reading previously calculated values'
        f = open(log_path, 'r')
        # Skip the first line (header for time array)
        f.readline()
        for line in f:
            try:
                time.append(float(line))
            except (ValueError):
                # Reached the header for the next variable
                break
        #for line in f:
        #    try:
        #        ohc.append(float(line))
        #    except (ValueError):
        #        break
        #for line in f:
        #    try:
        #        totalsalt.append(float(line))
        #    except (ValueError):
        #        break
        for line in f:
            try:
                avgismr.append(float(line))
            except (ValueError):
                break
        for line in f:
            try:
                massloss.append(float(line))
            except (ValueError):
                break
        #for line in f:
        #    try:
        #        tke.append(float(line))
        #    except (ValueError):
        #        break
        #for line in f:
        #    try:
        #        maxvel.append(float(line))
        #    except (ValueError):
        #        break
        for line in f:
            try:
                drakepsgtrans.append(float(line))
            except (ValueError):
                break
        for line in f:
            try:
                totalice.append(float(line))
            except(ValueError):
                break
        for line in f:
            try:
                totalfwflux.append(float(line))
            except(ValueError):
                break
        for line in f:
            bwtemp.append(float(line))
        f.close()

    # Calculate differentials
    print 'Analysing grid'
    dA, dV, dy_wct = calc_grid(file_path)
    # Read time data and convert from seconds to years
    id = Dataset(file_path, 'r')
    new_time = id.variables['ocean_time'][:]/(365.25*24*60*60)
    id.close()
    # Concatenate with time values from log file
    for t in range(size(new_time)):
        time.append(new_time[t])

    # Process each timestep separately to prevent memory overflow
    for t in range(size(new_time)):
        print 'Processing timestep '+str(t+1)+' of '+str(size(new_time))
        rho = get_rho(file_path, t)
        #print 'Calculating ocean heat content'
        #ohc.append(calc_ohc(file_path, dV, rho, t))
        #print 'Calculating total salt content'
        #totalsalt.append(calc_totalsalt(file_path, dV, rho, t))
        print 'Calculating average ice shelf melt rate'
        avgismr_tmp, ismr = calc_avgismr(file_path, dA, t)
        avgismr.append(avgismr_tmp)
        print 'Calculating basal mass loss'
        massloss.append(calc_massloss(ismr, dA))
        #print 'Calculating total kinetic energy'
        #tke_tmp, u_rho, v_rho = calc_tke(file_path, dV, rho, t)
        #tke.append(tke_tmp)
        #print 'Calculating maximum velocity'
        #maxvel.append(calc_maxvel(u_rho, v_rho))
        print 'Calculating Drake Passage transport'
        drakepsgtrans.append(calc_drakepsgtrans(file_path, dy_wct, t))
        print 'Calculating total sea ice extent'
        totalice.append(calc_totalice(cice_path, dA, t))
        print 'Calculating total sea ice-to-ocean freshwater flux'
        totalfwflux.append(calc_totalfwflux(cice_path, dA, t))
        print 'Calculating average bottom water temperature in ice shelf cavities'
        bwtemp.append(calc_bwtemp(file_path, dA, t))

    # Plot each timeseries in sequence
    #print 'Plotting ocean heat content'
    #clf()
    #plot(time, ohc)
    #xlabel('Years')
    #ylabel('Southern Ocean Heat Content (J)')
    #savefig('ohc.png')
    #print 'Plotting total salt content'
    #clf()
    #plot(time, totalsalt)
    #xlabel('Years')
    #ylabel('Southern Ocean Salt Content (kg)')
    #savefig('totalsalt.png')
    print 'Plotting average ice shelf melt rate'
    clf()
    plot(time, avgismr)
    xlabel('Years')
    ylabel('Area-averaged Ice Shelf Melt Rate (m/y)')
    savefig('avgismr.png')
    print 'Plotting basal mass loss'
    clf()
    plot(time, massloss)
    xlabel('Years')
    ylabel('Ice Shelf Basal Mass Loss (Gt/y)')
    savefig('massloss.png')
    #print 'Plotting total kinetic energy'
    #clf()
    #plot(time, tke)
    #xlabel('Years')
    #ylabel('Southern Ocean Total Kinetic Energy (J)')
    #savefig('tke.png')
    #print 'Plotting maximum velocity'
    #clf()
    #plot(time, maxvel)
    #xlabel('Years')
    #ylabel('Maximum Southern Ocean Velocity (m/s)')
    #savefig('maxvel.png')
    print 'Plotting Drake Passage transport'
    clf()
    plot(time, drakepsgtrans)
    xlabel('Years')
    ylabel('Drake Passage Transport (Sv)')
    savefig('drakepsgtrans.png')
    print 'Plotting total sea ice extent'
    clf()
    plot(time, totalice)
    xlabel('Years')
    ylabel(r'Total Sea Ice Extent (million km$^2$)')
    savefig('totalice.png')
    print 'Plotting total sea ice-to-ocean freshwater flux'
    clf()
    plot(time, totalfwflux)
    xlabel('Years')
    ylabel('Sea Ice-to-Ocean Freshwater Flux (Sv)')
    savefig('totalfwflux.png')
    print 'Plotting bottom water temperature'
    clf()
    plot(time, bwtemp)
    xlabel('Years')
    ylabel(r'Average Bottom Water Temperature in Ice Shelf Cavities ($^{\circ}$C)')
    savefig('bwtemp.png')

    print 'Saving results to log file'
    f = open(log_path, 'w')
    f.write('Time (years):\n')
    for elm in time:
        f.write(str(elm) + '\n')
    #f.write('Southern Ocean Heat Content (J):\n')
    #for elm in ohc:
    #    f.write(str(elm) + '\n')
    #f.write('Southern Ocean Salt Content (kg):\n')
    #for elm in totalsalt:
    #    f.write(str(elm) + '\n')
    f.write('Area-averaged Ice Shelf Melt Rate (m/y):\n')
    for elm in avgismr:
        f.write(str(elm) + '\n')
    f.write('Ice Shelf Basal Mass Loss (Gt/y):\n')
    for elm in massloss:
        f.write(str(elm) + '\n')
    #f.write('Southern Ocean Total Kinetic Energy (J):\n')
    #for elm in tke:
    #    f.write(str(elm) + '\n')
    #f.write('Maximum Southern Ocean Velocity (m/s):\n')
    #for elm in maxvel:
    #    f.write(str(elm) + '\n')
    f.write('Drake Passage Transport (Sv):\n')
    for elm in drakepsgtrans:
        f.write(str(elm) + '\n')
    f.write('Total Sea Ice Extent (million km^2):\n')
    for elm in totalice:
        f.write(str(elm) + '\n')
    f.write('Total Sea Ice-to-Ocean Freshwater Flux (Sv):\n')
    for elm in totalfwflux:
        f.write(str(elm) + '\n')
    f.write('Average Bottom Water Temperature in Ice Shelf Cavities (C):\n')
    for elm in bwtemp:
        f.write(str(elm) + '\n')
    f.close()


# Command-line interface
if __name__ == "__main__":

    file_path = raw_input('Enter path to ocean history/averages file: ')
    cice_path = raw_input('Enter path to CICE history file: ')
    log_path = raw_input('Enter path to log file to save values and/or read previously calculated values: ')

    spinup_plots(file_path, cice_path, log_path)


