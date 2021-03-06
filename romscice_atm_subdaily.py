from netCDF4 import Dataset
from numpy import *
from interp_era2roms import *

# Convert two ERA-Interim files:
# AN_yyyy_subdaily_orig.nc: one year of 6-hour measurements for surface pressure
#                           (sp), 2-metre temperature (t2m) and dew point (d2m),
#                           total cloud cover (tcc), and 10-metre winds (u10, 
#                           v10)
# FC_yyyy_subdaily_orig.nc: one year of 12-hour measurements for total 
#                           precipitation (tp), snowfall (sf), and evaporation
#                           (e)
# to two ROMS-CICE input forcing files with the correct units and naming 
# conventions, and winds rotated correctly:
# AN_yyyy_subdaily.nc: one year of 6-hour measurements for surface pressure
#                   (Pair), temperature (Tair), specific humidity (Qair), 
#                   cloud fraction (cloud), and winds (Uwind, Vwind)
# FC_yyyy_subdaily.nc: one year of 12-hour measurements for rainfall (rain),
#                   snowfall (snow), and evaporation 
# Input: year = integer containing the year to process
#        count = time record in the given year to start with

# This script only processes 100 6-hour timesteps (50 12-hour timesteps) at
# once to prevent memory overflow, and is designed to be called by a self-
# submitting batch script. See convert_era.job for an example.

def convert_file (year, count):

    # Make sure input arguments are integers (sometimes the batch script likes
    # to pass them as strings)
    year = int(year)
    count = int(count)

    # Paths of ROMS grid file, input ERA-Interim files, and output ROMS-CICE
    # files; other users will need to change these
    grid_file = '/short/m68/kaa561/metroms_iceshelf/apps/common/grid/circ30S_quarterdegree.nc'
    input_atm_file = '/short/m68/kaa561/metroms_iceshelf/data/originals/ERA_Interim/AN_' + str(year) + '_subdaily_orig.nc'
    input_ppt_file = '/short/m68/kaa561/metroms_iceshelf/data/originals/ERA_Interim/FC_' + str(year) + '_subdaily_orig.nc'
    output_atm_file = '/short/m68/kaa561/metroms_iceshelf/data/ERA_Interim/AN_' + str(year) + '_subdaily.nc'
    output_ppt_file = '/short/m68/kaa561/metroms_iceshelf/data/ERA_Interim/FC_' + str(year) + '_subdaily.nc'
    logfile = str(year) + '.log'

    Lv = 2.5e6 # Latent heat of vapourisation, J/kg
    Rv = 461.5 # Ideal gas constant for water vapour, J/K/kg

    if count == 0:
        log = open(logfile, 'w')
    else:
        log = open(logfile, 'a')
    log.write('Reading grids\n')
    log.close()

    # Read ROMS latitude and longitude
    grid_fid = Dataset(grid_file, 'r')
    lon_roms = grid_fid.variables['lon_rho'][:,:]
    lat_roms = grid_fid.variables['lat_rho'][:,:]
    angle = grid_fid.variables['angle'][:,:]
    grid_fid.close()
    num_lon = size(lon_roms, 1)
    num_lat = size(lon_roms, 0)

    # Open input AN file and read time values
    iatm_fid = Dataset(input_atm_file, 'r')
    atm_time = iatm_fid.variables['time'][:] # hours since 1900-01-01 00:00:0.0
    # Convert time units
    atm_time = atm_time/24.0 # days since 1900-01-01 00:00:0.0
    atm_time = atm_time - 92*365 - 22 # days since 1992-01-01 00:00:0.0; note that there were 22 leap years between 1900 and 1992
    # Also read ERA-Interim latitude and longitude
    lon_era = iatm_fid.variables['longitude'][:]
    lat_era = iatm_fid.variables['latitude'][:]
    iatm_fid.close()

    if count == 0:
        log = open(logfile, 'a')
        log.write('Setting up ' + output_atm_file + '\n')
        log.close()

        oatm_fid = Dataset(output_atm_file, 'w')
        # Define dimensions (note unlimited time dimension)
        oatm_fid.createDimension('xi_rho', num_lon)
        oatm_fid.createDimension('eta_rho', num_lat)
        oatm_fid.createDimension('time', None)
        # Define variables; write latitude and longitude since they are not
        # time-dependent
        oatm_fid.createVariable('lon_rho', 'f8', ('eta_rho', 'xi_rho'))
        oatm_fid.variables['lon_rho'].long_name = 'longitude of rho-points'
        oatm_fid.variables['lon_rho'].units = 'degree_east'
        oatm_fid.variables['lon_rho'][:,:] = lon_roms
        oatm_fid.createVariable('lat_rho', 'f8', ('eta_rho', 'xi_rho'))
        oatm_fid.variables['lat_rho'].long_name = 'latitude of rho-points'
        oatm_fid.variables['lat_rho'].units = 'degree_north'
        oatm_fid.variables['lat_rho'][:,:] = lat_roms
        oatm_fid.createVariable('time', 'f8', ('time'))
        oatm_fid.variables['time'].units = 'days since 1992-01-01 00:00:0.0'
        oatm_fid.createVariable('Pair', 'f8', ('time', 'eta_rho', 'xi_rho'))
        oatm_fid.variables['Pair'].long_name = 'surface air pressure'
        oatm_fid.variables['Pair'].units = 'Pascal'
        oatm_fid.createVariable('Tair', 'f8', ('time', 'eta_rho', 'xi_rho'))
        oatm_fid.variables['Tair'].long_name = 'surface air temperature'
        oatm_fid.variables['Tair'].units = 'Celsius'
        oatm_fid.createVariable('Qair', 'f8', ('time', 'eta_rho', 'xi_rho'))
        oatm_fid.variables['Qair'].long_name = 'surface relative humidity'
        oatm_fid.variables['Qair'].units = 'kg/kg'
        oatm_fid.createVariable('cloud', 'f8', ('time', 'eta_rho', 'xi_rho'))
        oatm_fid.variables['cloud'].long_name = 'cloud fraction'
        oatm_fid.variables['cloud'].units = 'nondimensional'
        oatm_fid.createVariable('Uwind', 'f8', ('time', 'eta_rho', 'xi_rho'))
        oatm_fid.variables['Uwind'].long_name = 'surface u-wind component'
        oatm_fid.variables['Uwind'].units = 'm/s'
        oatm_fid.createVariable('Vwind', 'f8', ('time', 'eta_rho', 'xi_rho'))
        oatm_fid.variables['Vwind'].long_name = 'surface v-wind component'
        oatm_fid.variables['Vwind'].units = 'm/s'
        oatm_fid.close()

    log = open(logfile, 'a')
    log.write('Processing 6-hourly data\n')
    log.close()

    # Process one timestep at a time to minimise memory use
    for t in range(count, count+100):
        if t >= size(atm_time):
            break
        oatm_fid = Dataset(output_atm_file, 'a')
        log = open(logfile, 'a')
        log.write('Processing record ' + str(t+1) + ' of ' + str(size(atm_time)) + '\n')
        log.close()
        # Write the current time value to output AN file
        oatm_fid.variables['time'][t] = atm_time[t]
        # Read variables for this timestep
        iatm_fid = Dataset(input_atm_file, 'r')
        sp = transpose(iatm_fid.variables['sp'][t,:,:])
        t2m = transpose(iatm_fid.variables['t2m'][t,:,:])
        d2m = transpose(iatm_fid.variables['d2m'][t,:,:])
        tcc = transpose(iatm_fid.variables['tcc'][t,:,:])
        u10 = transpose(iatm_fid.variables['u10'][t,:,:])
        v10 = transpose(iatm_fid.variables['v10'][t,:,:])
        iatm_fid.close()
        # Calculate relative humidity from temperature and dew point
        rh = exp(Lv/Rv*(t2m**(-1) - d2m**(-1)))
        # Interpolate each variable to ROMS grid and write to output AN file
        pair = interp_era2roms(sp, lon_era, lat_era, lon_roms, lat_roms)
        oatm_fid.variables['Pair'][t,:,:] = pair
        tair = interp_era2roms(t2m, lon_era, lat_era, lon_roms, lat_roms)
        oatm_fid.variables['Tair'][t,:,:] = tair-273.15
        qair = interp_era2roms(rh, lon_era, lat_era, lon_roms, lat_roms)
        # Constrain humidity values to be between 0 and 1
        qair[qair < 0] = 0.0
        qair[qair > 1] = 1.0
        oatm_fid.variables['Qair'][t,:,:] = qair
        cloud = interp_era2roms(tcc, lon_era, lat_era, lon_roms, lat_roms)
        # Constrain cloud fractions to be between 0 and 1
        cloud[cloud < 0] = 0.0
        cloud[cloud > 1] = 1.0
        oatm_fid.variables['cloud'][t,:,:] = cloud
        uwind_lonlat = interp_era2roms(u10, lon_era, lat_era, lon_roms, lat_roms)
        vwind_lonlat = interp_era2roms(v10, lon_era, lat_era, lon_roms, lat_roms)
        # Rotate winds to ROMS grid
        uwind = uwind_lonlat*cos(angle) + vwind_lonlat*sin(angle)
        vwind = vwind_lonlat*cos(angle) - uwind_lonlat*sin(angle)
        oatm_fid.variables['Uwind'][t,:,:] = uwind
        oatm_fid.variables['Vwind'][t,:,:] = vwind
        oatm_fid.close()

    # Open input FC file and read time values
    ippt_fid = Dataset(input_ppt_file, 'r')
    ppt_time = ippt_fid.variables['time'][:] # hours since 1900-01-01 00:00:0.0
    # Convert time units
    ppt_time = ppt_time/24.0 # days since 1900-01-01 00:00:0.0
    ppt_time = ppt_time - 92*365 - 22 # days since 1992-01-01 00:00:0.0; note that there were 22 leap years between 1900 and 1992
    ppt_time = ppt_time - 0.5 # switch from precipitation over the preceding 12 hours to precipitation over the following 12 hours; this is easier for ROMS
    ippt_fid.close()

    if count == 0:
        log = open(logfile, 'a')
        log.write('Setting up ' + output_ppt_file + '\n')
        log.close()

        oppt_fid = Dataset(output_ppt_file, 'w')
        # Define dimensions
        oppt_fid.createDimension('xi_rho', num_lon)
        oppt_fid.createDimension('eta_rho', num_lat)
        oppt_fid.createDimension('time', None)
        # Define variables
        oppt_fid.createVariable('lon_rho', 'f8', ('eta_rho', 'xi_rho'))
        oppt_fid.variables['lon_rho'].long_name = 'longitude of rho-points'
        oppt_fid.variables['lon_rho'].units = 'degree_east'
        oppt_fid.variables['lon_rho'][:,:] = lon_roms
        oppt_fid.createVariable('lat_rho', 'f8', ('eta_rho', 'xi_rho'))
        oppt_fid.variables['lat_rho'].long_name = 'latitude of rho-points'
        oppt_fid.variables['lat_rho'].units = 'degree_north'
        oppt_fid.variables['lat_rho'][:,:] = lat_roms
        oppt_fid.createVariable('time', 'f8', ('time'))
        oppt_fid.variables['time'].units = 'days since 1992-01-01 00:00:0.0'
        oppt_fid.createVariable('rain', 'f8', ('time', 'eta_rho', 'xi_rho'))
        oppt_fid.variables['rain'].long_name = 'rain fall rate'
        oppt_fid.variables['rain'].units = 'm_per_12hr'
        oppt_fid.createVariable('snow', 'f8', ('time', 'eta_rho', 'xi_rho'))
        oppt_fid.variables['snow'].long_name = 'snow fall rate'
        oppt_fid.variables['snow'].units = 'm_per_12hr'
        oppt_fid.createVariable('evaporation', 'f8', ('time', 'eta_rho', 'xi_rho'))
        oppt_fid.variables['evaporation'].long_name = 'evaporation rate'
        oppt_fid.variables['evaporation'].units = 'm_per_12hr'
        oppt_fid.close()

    log = open(logfile, 'a')
    log.write('Processing 12-hourly data\n')
    log.close()

    for t in range(count/2, (count+100)/2):
        if t >= size(ppt_time):
            break
        oppt_fid = Dataset(output_ppt_file, 'a')
        log = open(logfile, 'a')
        log.write('Processing record ' + str(t+1) + ' of ' + str(size(ppt_time)) + '\n')
        log.close()
        # Write the current time value to output FC file
        oppt_fid.variables['time'][t] = ppt_time[t]
        # Read data for this timestep
        ippt_fid = Dataset(input_ppt_file, 'r')
        tp = transpose(ippt_fid.variables['tp'][t,:,:])
        sf = transpose(ippt_fid.variables['sf'][t,:,:])
        e = -1*transpose(ippt_fid.variables['e'][t,:,:])
        ippt_fid.close()
        # Interpolate to ROMS grid and write to output FC file
        rain = interp_era2roms(tp, lon_era, lat_era, lon_roms, lat_roms)
        snow = interp_era2roms(sf, lon_era, lat_era, lon_roms, lat_roms)
        evap = interp_era2roms(e, lon_era, lat_era, lon_roms, lat_roms)
        # Make sure there are no negative values for precip
        rain[rain < 0] = 0.0
        oppt_fid.variables['rain'][t,:,:] = rain
        snow[snow < 0] = 0.0
        oppt_fid.variables['snow'][t,:,:] = snow
        # Negative values are allowed for evaporation (they mean condensation)
        oppt_fid.variables['evaporation'][t,:,:] = evap
        oppt_fid.close()

    log = open(logfile, 'a')
    log.write('Finished\n')
    log.close()
