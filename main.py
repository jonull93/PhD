# %%
# from gams import *
import pickle  # for dumping and loading variable to/from file
import os

indicators = ["cost_tot",
              "VRE_share_total",
              'curtailment',
              #              'flywheel',
              "G",
              'sync_cond',
              'bat',
              'FC',
              'H2store',
              'EB', 'HP',
              ]
cases = []
h = 6
systemFlex = ["lowFlex", "highFlex"]
modes = ["noFC"]#, "fullFC"]  #, "inertia", "OR", "FCnoPTH", "FCnoH2", "FCnoWind", "FCnoBat", "FCnoSynth"]
for reg in ["iberia", "brit", "nordic"]:
    for flex in systemFlex:
        for mode in modes:
            for year in [2030, 2040, 2050]:
                cases.append(f"{reg}_{flex}_{mode}_{year}{'_'+str(h)+'h' if h>1 else ''}_noLateG_CO2cap2050")

# cases.append("OR_ES3_noSyn_noDoubleUse") exec(open("./seasons.py").read()) run_output = input("Enter 'r' to read
# pickled data, 'w' to (over)write or 'rw' to add missing scenarios: ")
run_output = "w"
# run_plots = input('Should we also plot results? Y/N: ')
run_plots = "n"
overwrite = []  # [reg+"_inertia_0.1x" for reg in ["ES3", "HU", "IE", "SE2"]]+[reg+"_inertia" for reg in ["ES3", "HU", "IE", "SE2"]]+[reg+"_inertia_noSyn" for reg in ["ES3", "HU", "IE", "SE2"]]
name = f"results_{h}h_noLateG_CO2cap2050"  # this will be the name of the file: output_%NAME%.xlsx
if "PLIA" in os.environ['COMPUTERNAME']:
    path = "C:\\Users\\Jonathan\\Box\\python\\output\\"
    gdxpath = "C:\\git\\multinode\\"  # where to find gdx files
else:
    path = "D:\\Jonathan\\python\\output\\"
    gdxpath = "D:\\Jonathan\\multinode\\"

# path = "C:\\Users\\jonull\\Box\\python\\output\\"
# gdxpath = "C:\\models\\multinode\\"  # where to find gdx files

if run_output.lower() == "r" or run_output.lower() == "read":
    try:
        old_data = pickle.load(open("PickleJar\\data_" + name + ".txt", "rb"))
    except:
        oops = input(
            "data.txt failed to load! type 'abort' to abort, or anything else to load output.py and write new data: ")
        if oops.lower() == "abort":
            print("aborted")
        else:
            data = {}
            exec(open("./output_v3.py").read())

elif run_output.lower() == "w" or run_output.lower() == "write":
    old_data = {}
    excel = True
    exec(open("./output_v3.py").read())
elif run_output.lower() == "rw":
    try: old_data = pickle.load(open("PickleJar\\data_" + name + ".pickle", "rb"))
    except FileNotFoundError:
        old_data = {}
    excel = True
    exec(open("./output_v3.py").read())
else:
    print("'r', 'w' or 'rw', try again")

if run_plots.lower() == "y" or run_plots.lower() == "yes":

    # -- PLOTTING --

    import matplotlib.pyplot as plt

    w = 0.3
    p = 0
    f1 = plt.figure(1)
    y_label = ['System cost [G euro]', 'VRE share []', 'PtH share in DH system []', 'Total TES capacity [GWh]']
    for i in indicators[0:2]:
        c = 0
        p += 1
        ax = plt.subplot(2, 2, p)
        if p % 2 == 0:
            ax.yaxis.tick_right()
            # ax.yaxis.set_label_position("right")
        for k in cases:
            c += 1
            nT = data[k][i]
            mT = data[k + '_TES'][i]
            # sT = data[k+'_TES_stratified'][i]
            ax.set_ylabel(y_label[p - 1])
            ax.bar(c - w, nT, width=w, color='xkcd:brick red', align='center')
            ax.bar(c, mT, width=w, color='xkcd:gold', align='center')
            # ax.bar(c+w, sT, width=w, color='xkcd:army green',align='center')
            plt.xticks([1, 2, 3, 4], cases)
    # plt.legend(['no TES', 'mixed', 'stratified'],loc=9, bbox_to_anchor=(-0.2, -0.12), ncol=3)
    art = []
    bars = ['no TES', 'Mixed', 'Stratified']
    lgd = plt.legend(bars, loc=9, bbox_to_anchor=(-0.2, -0.12), ncol=3)
    art.append(lgd)
    name = "stratified_TES_2indicators"
    plt.savefig(name + ".png", additional_artists=art, bbox_inches="tight")
    plt.savefig(name + ".svg", additional_artists=art, bbox_inches="tight")

    f2 = plt.figure(2)
    c = 0

    ax2 = plt.subplot(111)

    colors = {'winter': 'xkcd:pale blue', 'spring': 'xkcd:light green', 'summer': 'xkcd:grass green',
              'fall': 'xkcd:burnt sienna'}
    for k in cases:
        c += 1
        # print(nT)
        # print(mT)
        # print(sT)
        nT = []
        mT = []
        sT = []
        line = []
        p = 0
        for i in season:
            nT.append(data[k]['heat'][i])
            mT.append(data[k + '_TES']['heat'][i])
            # sT.append(data[k+'_TES_stratified']['heat'][i])
            #
            # print(nT[-1])
            line.append(
                ax2.bar(c - w, nT[-1], width=w - 0.03, align='center', color=colors[i], bottom=sum(nT) - nT[-1]))
            ax2.bar(c, mT[-1], width=w - 0.03, align='center', color=colors[i], bottom=sum(mT) - mT[-1])
            # ax2.bar(c+w, sT[-1], width=w-0.03, align='center', color=colors[i], bottom = sum(sT)-sT[-1])
            p += 1

    plt.xticks([1, 2, 3, 4], cases)
    axes_index = []

    for i in range(1, 5):
        axes_index.append(i - w)
        axes_index.append(i)
        axes_index.append(i + w)
    c = 0

    for i in axes_index:
        ax2.text(axes_index[c], 150, [bars * 4][0][c], rotation=90, horizontalalignment='center',
                 verticalalignment='bottom')
        c += 1

    ax2.set_ylabel('Heat generation [GWh]')
    # ax2.legend()
    art = []
    lgd = plt.legend(line[0:4], ['Winter', 'Spring', 'Summer', 'Fall'], loc=9, bbox_to_anchor=(0.5, -0.07), ncol=4)
    art.append(lgd)
    name = "base_VMSC"
    plt.savefig(name + ".png", additional_artists=art, bbox_inches="tight")
    plt.savefig(name + ".svg", additional_artists=art, bbox_inches="tight")

    # plt.xticks(axes_index, ['no TES', 'Mixed', 'Stratified']*4,rotation=90)
    plt.show()
