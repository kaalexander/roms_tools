from netCDF4 import *
from numpy import *
from matplotlib.pyplot import *
#import colormaps as cmaps

# Create a 2x1 plot of mixed layer depth (calculated by KPP) on 23 August (the
# sea ice area max) for the U3_LIM experiment, and anomalies for the C4_LD
# experiment.
def adv_mld_2 ():

    # Paths to simulation directories
    paths = ['/short/m68/kaa561/advection/u3_lim/', '/short/m68/kaa561/advection/c4_l/']
    # Titles for plotting
    labels = ['a) U3_LIM', 'b) C4_LD - U3_LIM']
    # File name: daily average for 23 August
    file_tail = 'ocean_avg_0001.nc'
    # If 23 August doesn't have its own file, put the time index here
    tstep = 236

    # Bounds and ticks for colour scales
    max_abs = 600 #800
    tick_abs = 200
    max_anom = 300 #400
    tick_anom = 150 #200

    # Degrees to radians conversion factor
    deg2rad = pi/180.
    # Centre of missing circle in grid
    lon_c = 50
    lat_c = -83
    # Radius of missing circle
    radius = 10.5
    # Boundary of regular grid to embed circle in
    circle_bdry = -70+90

    lon_ticks = array([-120, -60, 60, 120, 180])
    lat_ticks = array([-44, -42, -42, -44, -41])
    lon_labels = [r'120$^{\circ}$W', r'60$^{\circ}$W', r'60$^{\circ}$E', r'120$^{\circ}$E', r'180$^{\circ}$']
    lon_rot = [-60, 60, -60, 60, 0]

    # Read mixed layer depth from U3_LIM simulation; also grid and mask
    # variables
    id = Dataset(paths[0]+file_tail, 'r')
    data = id.variables['Hsbl'][tstep-1,:350,1:]
    lon = id.variables['lon_rho'][:350,1:]
    lat = id.variables['lat_rho'][:350,1:]
    mask = id.variables['mask_rho'][:350,1:]
    zice = id.variables['zice'][:350,1:]
    id.close()

    # Mask out the ice shelf cavities and switch sign on mixed layer depth
    index = zice != 0
    mask[index] = 0.0
    data0 = ma.masked_where(zice!=0, -data)

    # Land mask
    land = ma.masked_where(mask==1, mask)

    # Circumpolar x and y coordinates for plotting
    x = -(lat+90)*cos(lon*deg2rad+pi/2)
    y = (lat+90)*sin(lon*deg2rad+pi/2)
    # Coordinates of centre of missing circle
    x_c = -(lat_c+90)*cos(lon_c*deg2rad+pi/2)
    y_c = (lat_c+90)*sin(lon_c*deg2rad+pi/2)
    # Longitude labels
    x_ticks = -(lat_ticks+90)*cos(lon_ticks*deg2rad+pi/2)
    y_ticks = (lat_ticks+90)*sin(lon_ticks*deg2rad+pi/2)
    # Regular grid to embed missing circle in 
    x_reg, y_reg = meshgrid(linspace(-circle_bdry, circle_bdry, num=100), linspace(-circle_bdry, circle_bdry, num=100))
    # Mask everything except the circle out of the regular grid
    land_circle = zeros(shape(x_reg))
    land_circle = ma.masked_where(sqrt((x_reg-x_c)**2 + (y_reg-y_c)**2) > radius, land_circle)

    # Set up figure
    fig = figure(figsize=(20,10))
    ax = fig.add_subplot(1, 2, 1, aspect='equal')
    # First shade land
    contourf(x, y, land, 1, colors=(('0.6', '0.6', '0.6')))
    # Fill in missing circle
    contourf(x_reg, y_reg, land_circle, 1, colors=(('0.6', '0.6', '0.6')))
    # Shade the mixed layer depth (pcolor not contourf so we don't misrepresent
    # the model grid)
    img0 = pcolor(x, y, data0, vmin=0, vmax=max_abs, cmap='jet') #cmaps.viridis)
    # Add longitude labels
    for i in range(size(x_ticks)):
        text(x_ticks[i], y_ticks[i], lon_labels[i], ha='center', rotation=lon_rot[i])
    axis('off')
    # Add title
    title(labels[0], fontsize=20)
    # Add colorbar
    cbaxes0 = fig.add_axes([0.05, 0.15, 0.02, 0.7])
    cbar0 = colorbar(img0, ticks=arange(0, max_abs+tick_abs, tick_abs), cax=cbaxes0, extend='max')
    cbar0.ax.tick_params(labelsize=16)  

    # Read mixed layer depth
    id = Dataset(paths[1]+file_tail, 'r')
    data = id.variables['Hsbl'][tstep-1,:350,1:]
    id.close()
    # Mask out the ice shelf cavities and switch sign
    data = ma.masked_where(zice!=0, -data)
    # Calculate anomaly from U3_LIM
    data = data - data0
    # Add to plot, same as before
    ax = fig.add_subplot(1, 2, 2, aspect='equal')
    contourf(x, y, land, 1, colors=(('0.6', '0.6', '0.6')))
    contourf(x_reg, y_reg, land_circle, 1, colors=(('0.6', '0.6', '0.6')))
    img = pcolor(x, y, data, vmin=-max_anom, vmax=max_anom, cmap='RdBu_r')
    axis('off')
    title(labels[1], fontsize=20)
    cbaxes = fig.add_axes([0.92, 0.15, 0.02, 0.7])
    cbar = colorbar(img, ticks=arange(-max_anom, max_anom+tick_anom, tick_anom), cax=cbaxes, extend='both')
    cbar.ax.tick_params(labelsize=16)

    # Main title
    suptitle('Mixed layer depth (m) on 23 August', fontsize=28)

    #fig.show()
    fig.savefig('adv_mld_2.png')


# Command-line interface
if __name__ == '__main__':

    adv_mld_2()
    
