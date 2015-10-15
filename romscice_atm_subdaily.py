from netCDF4 import Dataset
from numpy import *
from scipy.interpolate import LinearNDInterpolator, RectBivariateSpline

# Convert two ERA-Interim files:
# AN_yyyy_unlim_orig.nc: one year of 6-hour measurements for surface pressure 
#                        (sp), 2-metre temperature (t2m) and dew point (d2m),
#                        total cloud cover (tcc), and 10-metre winds (u10, v10)
# FC_yyyy_unlim_orig.nc: one year of 12-hour measurements for total 
#                        precipitation (tp) 
# to two ROMS-CICE input forcing files with the correct units and naming 
# conventions:
# AN_yyyy_unlim.nc: one year of 6-hour measurements for surface pressure
#                   (Pair), temperature (Tair), specific humidity (Qair), 
#                   cloud fraction (cloud), and winds (Uwind, Vwind)
# FC_yyyy_unlim.nc: one year of 12-hour measurements for rainfall (rain)
# Input: year = integer containing the year to process

def convert_file (year):

    # Paths of ROMS grid file, input ERA-Interim files, and output ROMS-CICE
    # files; other users will need to change these
    grid_file = '/short/m68/kaa561/roms_circumpolar/data/caisom001_OneQuartergrd.nc'
    input_atm_file = 'data/ERA_Interim/AN_' + str(year) + '_unlim_orig.nc'
    input_ppt_file = 'data/ERA_Interim/FC_' + str(year) + '_unlim_orig.nc'
    output_atm_file = 'data/ERA_Interim/AN_' + str(year) + '_unlim.nc'
    output_ppt_file = 'data/ERA_Interim/FC_' + str(year) + '_unlim.nc'

    Lv = 2.5e6 # Latent heat of vapourisation, J/kg
    Rv = 461.5 # Ideal gas constant for water vapour, J/K/kg

    print 'Reading grids'

    # Read ROMS latitude and longitude
    grid_fid = Dataset(grid_file, 'r')
    lon_roms = grid_fid.variables['lon_rho'][:,:]
    lat_roms = grid_fid.variables['lat_rho'][:,:]
    grid_fid.close()
    num_lon = size(lon_roms, 1)
    num_lat = size(lon_roms, 0)

    # Open input AN file and read time values
    iatm_fid = Dataset(input_atm_file, 'r')
    atm_time = iatm_fid.variables['time'][:]
    atm_time = iatm_fid.variables['time'][:] # hours since 1900-01-01 00:00:0.0
    # Convert time units
    atm_time = atm_time/24 # days since 1900-01-01 00:00:0.0
    atm_time = atm_time - 70*365 - 17 # days since 1970-01-01 00:00:0.0; note that there were 17 leap years between 1900 and 1970
    # Also read ERA-Interim latitude and longitude
    lon_era = iatm_fid.variables['longitude'][:]
    lat_era = iatm_fid.variables['latitude'][:]

    print 'Setting up ' + output_atm_file

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
    oatm_fid.variables['time'].units = 'hours since 1900-01-01 00:00:0.0'
    oatm_fid.createVariable('Pair', 'f8', ('time', 'eta_rho', 'xi_rho'))
    oatm_fid.variables['Pair'].long_name = 'surface air pressure'
    oatm_fid.variables['Pair'].units = 'Pascal'
    oatm_fid.createVariable('Tair', 'f8', ('time', 'eta_rho', 'xi_rho'))
    oatm_fid.variables['Tair'].long_name = 'surface air temperature'
    oatm_fid.variables['Tair'].units = 'K'
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

    print 'Processing 6-hourly data'

    # Process one timestep at a time to minimise memory use
    for t in range(size(atm_time)):
        print 'Processing record ' + str(t+1) + ' of ' + str(size(atm_time))
        # Write the current time value to output AN file
        oatm_fid.variables['time'][t] = atm_time[t]
        # Read variables for this timestep
        sp = transpose(iatm_fid.variables['sp'][t,:,:])
        t2m = transpose(iatm_fid.variables['t2m'][t,:,:])
        d2m = transpose(iatm_fid.variables['d2m'][t,:,:])
        tcc = transpose(iatm_fid.variables['tcc'][t,:,:])
        u10 = transpose(iatm_fid.variables['u10'][t,:,:])
        v10 = transpose(iatm_fid.variables['v10'][t,:,:])
        # Calculate relative humidity from temperature and dew point
        rh = exp(Lv/Rv*(t2m**(-1) - d2m**(-1)))
        # Interpolate each variable to ROMS grid and write to output AN file
        pair = interp_era2roms(sp, lon_era, lat_era, lon_roms, lat_roms)
        oatm_fid.variables['Pair'][t,:,:] = pair
        tair = interp_era2roms(t2m, lon_era, lat_era, lon_roms, lat_roms)
        oatm_fid.variables['Tair'][t,:,:] = tair
        qair = interp_era2roms(rh, lon_era, lat_era, lon_roms, lat_roms)
        oatm_fid.variables['Qair'][t,:,:] = qair
        cloud = interp_era2roms(tcc, lon_era, lat_era, lon_roms, lat_roms)
        oatm_fid.variables['cloud'][t,:,:] = cloud
        uwind = interp_era2roms(u10, lon_era, lat_era, lon_roms, lat_roms)
        oatm_fid.variables['Uwind'][t,:,:] = uwind
        vwind = interp_era2roms(v10, lon_era, lat_era, lon_roms, lat_roms)
        oatm_fid.variables['Vwind'][t,:,:] = vwind

    iatm_fid.close()
    oatm_fid.close()        

    # Open input FC file and read time values
    ippt_fid = Dataset(input_ppt_file, 'r')
    ppt_time = ippt_fid.variables['time'][:] # hours since 1900-01-01 00:00:0.0
    # Convert time units
    ppt_time = ppt_time/24 # days since 1900-01-01 00:00:0.0
    ppt_time = ppt_time - 70*365 - 17 # days since 1970-01-01 00:00:0.0; note that there were 17 leap years between 1900 and 1970

    print 'Setting up ' + output_ppt_file

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
    oppt_fid.variables['time'].units = 'days since 1970-01-01 00:00:0.0'
    oppt_fid.createVariable('rain', 'f8', ('time', 'eta_rho', 'xi_rho'))
    oppt_fid.variables['rain'].long_name = 'rain fall rate'
    oppt_fid.variables['rain'].units = 'm per 12 hours'

    print 'Processing 12-hourly data'

    for t in range(size(ppt_time)):
        print 'Processing record ' + str(t+1) + ' of ' + str(size(ppt_time))
        # Write the current time value to output FC file
        oppt_fid.variables['time'][t] = ppt_time[t]
        # Read rainfall for this timestep
        tp = transpose(ippt_fid.variables['tp'][t,:,:])
        # Interpolate to ROMS grid and write to output FC file
        rain = interp_era2roms(tp, lon_era, lat_era, lon_roms, lat_roms)
        oppt_fid.variables['rain'][t,:,:] = rain

    ippt_fid.close()
    oppt_fid.close()


# Given an array on the ERA-Interim grid, interpolate any missing values, and
# then interpolate to the ROMS grid.
# Input:
# A = array of size nxm containing values on the ERA-Interim grid (first
#     dimension longitude, second dimension latitude)
# lon_era = array of length n containing ERA-Interim longitude values
# lat_era = array of length m containing ERA-Interim latitude values
# lon_roms = array of size pxq containing ROMS longitude values
# lat_roms = array of size pxq containing ROMS latitude values
# Output:
# B = array of size pxq containing values on the ROMS grid (first dimension
#     latitude, second dimension longitude)
def interp_era2roms (A, lon_era, lat_era, lon_roms, lat_roms):

    # Save the sizes of ROMS axes
    num_lon = size(lon_roms, 1)
    num_lat = size(lon_roms, 0)

    # Missing values are something <<0, but these can change when the offset
    # and scale factor attributes are automatically applied. Either way,
    # missing values will be the minimum values in A.
    flag = amin(A)

    # Interpolate missing values
    # I got this bit of code from Stack Exchange
    # It seems to work, not exactly sure how
    valid_mask = A > flag
    coords = array(nonzero(valid_mask)).T
    values = A[valid_mask]
    fill_function = LinearNDInterpolator(coords, values)
    Afill = fill_function(list(ndindex(A.shape))).reshape(A.shape)

    # Now interpolate from ERA-Interim grid to ROMS grid
    # First build a function to approximate A with 2D splines
    # Note that latitude has to be multiplied by -1 so both axes are strictly
    # ascending
    interp_function = RectBivariateSpline(lon_era, -lat_era, Afill)
    B = interp_function(list(lon_roms), list(-lat_roms))
    B = zeros(shape(lon_roms))
    # Call this function for each grid point individually - if you try to do
    # it all at once it throws a MemoryError
    for i in range(num_lon):
        for j in range(num_lat):
            B[j,i] = interp_function(lon_roms[j,i], -lat_roms[j,i])

    return B
        
    
    
        
        
    
    
    