from netCDF4 import Dataset
from numpy import *
from matplotlib.pyplot import *
from matplotlib import rcParams
from matplotlib.colors import LinearSegmentedColormap

# Make a circumpolar Antarctic figure showing the percentage change in mass
# loss for each ice shelf in the high-resolution FESOM simulation with respect
# to the low-resolution FESOM simulation, discarding the first 10 years
# (i.e. 2002-2016 average). Also print the values to the screen.
# Input:
# roms_grid = path to ROMS grid file
# fesom_logfile_lr, fesom_logfile_hr = path to FESOM logfiles from 
#                   timeseries_massloss.py in the fesomtools repository, for
#                   the low-resolution and high-resolution simulations
#                   respectively
# save = optional boolean indicating to save the figure to a file, rather than
#        display on screen
# fig_name = if save=True, filename for figure
def mip_massloss_difference_map (roms_grid, fesom_logfile_lr, fesom_logfile_hr, save=False, fig_name=None):

    # Year simulations start
    year_start = 1992
    # Years to analyse 
    obs_start = 2002
    obs_end = 2016
    # Number of output steps per year in FESOM
    peryear = 365/5

    # Limits on longitude and latitude for each ice shelf
    # These depend on the source geometry, in this case RTopo 1.05
    # Note there is one extra index at the end of each array; this is because
    # the Ross region crosses the line 180W and therefore is split into two
    lon_min = [-62.67, -65.5, -79.17, -85, -104.17, -102.5, -108.33, -114.5, -135.67, -149.17, -155, 144, 115, 94.17, 80.83, 65, 33.83, 19, 12.9, 9.33, -10.05, -28.33, -181, 158.33]
    lon_max = [-59.33, -60, -66.67, -28.33, -88.83, -99.17, -103.33, -111.5, -114.33, -140, -145, 146.62, 123.33, 102.5, 89.17, 75, 37.67, 33.33, 16.17, 12.88, 7.6, -10.33, -146.67, 181]
    lat_min = [-73.03, -69.35, -74.17, -83.5, -73.28, -75.5, -75.5, -75.33, -74.9, -76.42, -78, -67.83, -67.17, -66.67, -67.83, -73.67, -69.83, -71.67, -70.5, -70.75, -71.83, -76.33, -85, -84.5]
    lat_max = [-69.37, -66.13, -69.5, -74.67, -71.67, -74.17, -74.67, -73.67, -73, -75.17, -76.41, -66.67, -66.5, -64.83, -66.17, -68.33, -68.67, -68.33, -69.33, -69.83, -69.33, -71.5, -77.77, -77]
    # Name of each ice shelf
    names = ['Larsen D Ice Shelf', 'Larsen C Ice Shelf', 'Wilkins & George VI & Stange Ice Shelves', 'Ronne-Filchner Ice Shelf', 'Abbot Ice Shelf', 'Pine Island Glacier Ice Shelf', 'Thwaites Ice Shelf', 'Dotson Ice Shelf', 'Getz Ice Shelf', 'Nickerson Ice Shelf', 'Sulzberger Ice Shelf', 'Mertz Ice Shelf', 'Totten & Moscow University Ice Shelves', 'Shackleton Ice Shelf', 'West Ice Shelf', 'Amery Ice Shelf', 'Prince Harald Ice Shelf', 'Baudouin & Borchgrevink Ice Shelves', 'Lazarev Ice Shelf', 'Nivl Ice Shelf', 'Fimbul & Jelbart & Ekstrom Ice Shelves', 'Brunt & Riiser-Larsen Ice Shelves', 'Ross Ice Shelf']
    num_shelves = len(lon_min)-1

    # Degrees to radians conversion factor
    deg2rad = pi/180
    # Northern boundary 63S for plot
    nbdry = -63+90
    # Centre of missing circle in grid
    lon_c = 50
    lat_c = -83
    # Radius of missing circle (play around with this until it works)
    radius = 10.1
    # Minimum zice in ROMS grid
    min_zice = -10

    # Read FESOM timeseries
    # Start with low-res
    tmp = []
    f = open(fesom_logfile_lr, 'r')
    # Skip the first line (header)
    f.readline()
    # Count the number of time indices for the first variable (total mass loss
    # for all ice shelves, which we don't care about)
    num_time = 0
    for line in f:
        try:
            tmp = float(line)
            num_time += 1
        except(ValueError):
            # Reached the header for the next variable
            break
    # Set up array for mass loss values at each ice shelf
    fesom_massloss_ts_lr = empty([num_shelves, num_time])
    # Loop over ice shelves
    index = 0
    while index < num_shelves:
        t = 0
        for line in f:
            try:
                fesom_massloss_ts_lr[index,t] = float(line)
                t += 1
            except(ValueError):
                # Reached the header for the next ice shelf
                break
        index += 1
    # Average between observation years
    fesom_massloss_lr = mean(fesom_massloss_ts_lr[:,peryear*(obs_start-year_start):peryear*(obs_end+1-year_start)], axis=1)
    # Repeat for high-res
    tmp = []
    f = open(fesom_logfile_hr, 'r')
    f.readline()
    num_time = 0
    for line in f:
        try:
            tmp = float(line)
            num_time += 1
        except(ValueError):
            break
    fesom_massloss_ts_hr = empty([num_shelves, num_time])
    index = 0
    while index < num_shelves:
        t = 0
        for line in f:
            try:
                fesom_massloss_ts_hr[index,t] = float(line)
                t += 1
            except(ValueError):
                break
        index += 1
    fesom_massloss_hr = mean(fesom_massloss_ts_hr[:,peryear*(obs_start-year_start):peryear*(obs_end+1-year_start)], axis=1)

    # Read ROMS grid
    id = Dataset(roms_grid, 'r')
    lon = id.variables['lon_rho'][:-15,:-1]
    lat = id.variables['lat_rho'][:-15,:-1]
    mask_rho = id.variables['mask_rho'][:-15,:-1]
    mask_zice = id.variables['mask_zice'][:-15,:-1]
    zice = id.variables['zice'][:-15,:-1]
    id.close()
    # Make sure longitude goes from -180 to 180, not 0 to 360
    index = lon > 180
    lon[index] = lon[index] - 360
    # Get land/zice mask
    open_ocn = copy(mask_rho)
    open_ocn[mask_zice==1] = 0
    land_zice = ma.masked_where(open_ocn==1, open_ocn)

    # Initialise plotting field of ice shelf mass loss percentage change
    massloss_change = ma.empty(shape(lon))
    massloss_change[:,:] = ma.masked
    # Loop over ice shelves
    for index in range(num_shelves):
        # Calculate percentage change in massloss, high-res wrt low-res
        tmp = (fesom_massloss_hr[index] - fesom_massloss_lr[index])/fesom_massloss_lr[index]*100
        print names[index] + ': ' + str(tmp)
        # Modify plotting field for this region
        if index == num_shelves-1:
            # Ross region is split into two
            region = (lon >= lon_min[index])*(lon <= lon_max[index])*(lat >= lat_min[index])*(lat <= lat_max[index])*(mask_zice == 1) + (lon >= lon_min[index+1])*(lon <= lon_max[index+1])*(lat >= lat_min[index+1])*(lat <= lat_max[index+1])*(mask_zice == 1)
        else:
            region = (lon >= lon_min[index])*(lon <= lon_max[index])*(lat >= lat_min[index])*(lat <= lat_max[index])*(mask_zice == 1)
        massloss_change[region] = tmp

    # Edit zice so tiny ice shelves won't be contoured
    zice[massloss_change.mask] = 0.0
    # Convert grid to spherical coordinates
    x = -(lat+90)*cos(lon*deg2rad+pi/2)
    y = (lat+90)*sin(lon*deg2rad+pi/2)
    # Find centre in spherical coordinates
    x_c = -(lat_c+90)*cos(lon_c*deg2rad+pi/2)
    y_c = (lat_c+90)*sin(lon_c*deg2rad+pi/2)
    # Build a regular x-y grid and select the missing circle
    x_reg, y_reg = meshgrid(linspace(-nbdry, nbdry, num=1000), linspace(-nbdry, nbdry, num=1000))
    land_circle = zeros(shape(x_reg))
    land_circle = ma.masked_where(sqrt((x_reg-x_c)**2 + (y_reg-y_c)**2) > radius, land_circle)

    # Set up colour scale, -100 to max value, 0 is white
    bound = amax(abs(massloss_change))
    lev = linspace(amin(massloss_change), amax(massloss_change), num=50)
    min_colour = (amin(massloss_change)+bound)/(2.0*bound)
    max_colour = 1
    new_cmap = truncate_colormap(get_cmap('RdBu_r'), min_colour, max_colour)

    # Plot
    fig = figure(figsize=(16,12))
    ax = fig.add_subplot(1,1,1, aspect='equal')
    fig.patch.set_facecolor('white')
    # First shade land and zice in grey (include zice so there are no white
    # patches near the grounding line where contours meet)
    contourf(x, y, land_zice, 1, colors=(('0.6', '0.6', '0.6')))
    # Fill in the missing cicle
    contourf(x_reg, y_reg, land_circle, 1, colors=(('0.6', '0.6', '0.6')))
    # Now shade the percentage change in mass loss
    contourf(x, y, massloss_change, lev, cmap=new_cmap)
    cbar = colorbar(ticks=arange(0, bound+25, 25))
    cbar.ax.tick_params(labelsize=20)
    # Add a black contour for the ice shelf front
    rcParams['contour.negative_linestyle'] = 'solid'
    contour(x, y, zice, levels=[min_zice], colors=('black'))
    xlim([-nbdry, nbdry])
    ylim([-nbdry, nbdry])
    title('% Change in Ice Shelf Mass Loss ('+str(obs_start)+'-'+str(obs_end)+' average)\nfrom increased resolution in FESOM', fontsize=30)
    axis('off')

    # Finished
    if save:
        fig.savefig(fig_name)
    else:
        fig.show()


# Truncate colourmap function from https://stackoverflow.com/questions/40929467/how-to-use-and-plot-only-a-part-of-a-colorbar-in-matplotlib
def truncate_colormap(cmap, minval=0.0, maxval=1.0, n=-1):
    if n== -1:
        n = cmap.N
    new_cmap = LinearSegmentedColormap.from_list('trunc({name},{a:.2f},{b:.2f})'.format(name=cmap.name, a=minval, b=maxval), cmap(linspace(minval, maxval, n)))
    return new_cmap


if __name__ == "__main__":

    roms_grid = raw_input("Path to ROMS grid file: ")
    fesom_logfile_lr = raw_input("Path to FESOM low-res mass loss logfile: ")
    fesom_logfile_hr = raw_input("Path to FESOM high-res mass loss logfile: ")
    action = raw_input("Save figure (s) or display in window (d)? ")
    if action == 's':
        save = True
        fig_name = raw_input("File name for figure: ")
    elif action == 'd':
        save = False
        fig_name = None
    mip_massloss_difference_map(roms_grid, fesom_logfile_lr, fesom_logfile_hr, save, fig_name)
    
