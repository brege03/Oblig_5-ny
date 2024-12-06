# kgcontroller module
import pandas as pd
import numpy as np
from dbexcel import *
from kgmodel import *


# CRUD metoder

# Create

def insert_foresatt(f):
    global forelder
    new_id = 0
    if forelder.empty:
        new_id = 1
    else:
        new_id = forelder['foresatt_id'].max() + 1
    
    # sjekk for duplikater, om mulig
    if not forelder[forelder['foresatt_pnr'] == f.foresatt_pnr].empty:
        return forelder  # Returner hvis foresatt allerede finnes

    forelder = pd.concat([pd.DataFrame([[new_id,
                                        f.foresatt_navn,
                                        f.foresatt_adresse,
                                        f.foresatt_tlfnr,
                                        f.foresatt_pnr]],
                columns=forelder.columns), forelder], ignore_index=True)
    
    return forelder

def insert_barn(b):
    global barn
    new_id = 0
    if barn.empty:
        new_id = 1
    else:
        new_id = barn['barn_id'].max() + 1
    
    # sjekk for duplikater
    if not barn[barn['barn_pnr'] == b.barn_pnr].empty:
        return barn  # Returner hvis barn allerede finnes

    barn = pd.concat([pd.DataFrame([[new_id, b.barn_pnr]], columns=barn.columns), barn], ignore_index=True)
    
    return barn

def insert_soknad(s):
    global soknad
    new_id = 0
    if soknad.empty:
        new_id = 1
    else:
        new_id = soknad['sok_id'].max() + 1

    # sjekk for duplikater
    if not soknad[(soknad['foresatt_1'] == s.foresatt_1.foresatt_id) & (soknad['barn_1'] == s.barn_1.barn_id)].empty:
        return soknad  # Returner hvis søknad allerede finnes

    soknad = pd.concat([pd.DataFrame([[new_id,
                                     s.foresatt_1.foresatt_id,
                                     s.foresatt_2.foresatt_id,
                                     s.barn_1.barn_id,
                                     s.fr_barnevern,
                                     s.fr_sykd_familie,
                                     s.fr_sykd_barn,
                                     s.fr_annet,
                                     s.barnehager_prioritert,
                                     s.sosken__i_barnehagen,
                                     s.tidspunkt_oppstart,
                                     s.brutto_inntekt]],
                columns=soknad.columns), soknad], ignore_index=True)
    
    return soknad

# ---------------------------
# Read (select)

def select_alle_barnehager():
    """Returnerer en liste med alle barnehager definert i databasen dbexcel."""
    return barnehage.apply(lambda r: Barnehage(r['barnehage_id'],
                             r['barnehage_navn'],
                             r['barnehage_antall_plasser'],
                             r['barnehage_ledige_plasser']),
         axis=1).to_list()

def select_foresatt(f_navn):
    """OBS! Ignorerer duplikater"""
    series = forelder[forelder['foresatt_navn'] == f_navn]['foresatt_id']
    if series.empty:
        return np.nan
    else:
        return series.iloc[0] # returnerer kun det første elementet i series

def select_barn(b_pnr):
    """OBS! Ignorerer duplikater"""
    series = barn[barn['barn_pnr'] == b_pnr]['barn_id']
    if series.empty:
        return np.nan
    else:
        return series.iloc[0] # returnerer kun det første elementet i series

def select_alle_soknader():
    """Returnerer en liste med alle søknader definert i databasen dbexcel."""
    return soknad.apply(lambda r: Soknad(
                             r['sok_id'],
                             select_foresatt_by_id(r['foresatt_1']),
                             select_foresatt_by_id(r['foresatt_2']),
                             select_barn_by_id(r['barn_1']),
                             r['fr_barnevern'],
                             r['fr_sykd_familie'],
                             r['fr_sykd_barn'],
                             r['fr_annet'],
                             r['barnehager_prioritert'],
                             r['sosken__i_barnehagen'],
                             r['tidspunkt_oppstart'],
                             r['brutto_inntekt']),
         axis=1).to_list()

def select_foresatt_by_id(foresatt_id):
    """Henter foresatt basert på ID"""
    row = forelder[forelder['foresatt_id'] == foresatt_id]
    if not row.empty:
        r = row.iloc[0]
        return Foresatt(r['foresatt_id'], r['foresatt_navn'], r['foresatt_adresse'], r['foresatt_tlfnr'], r['foresatt_pnr'])
    return None

def select_barn_by_id(barn_id):
    """Henter barn basert på ID"""
    row = barn[barn['barn_id'] == barn_id]
    if not row.empty:
        r = row.iloc[0]
        return Barn(r['barn_id'], r['barn_pnr'])
    return None

# ------------------
# Update


# ------------------
# Delete


# ----- Persistent lagring ------
def commit_all():
    """Skriver alle dataframes til excel"""
    with pd.ExcelWriter('kgdata.xlsx', mode='a', if_sheet_exists='replace') as writer:  
        forelder.to_excel(writer, sheet_name='foresatt')
        barnehage.to_excel(writer, sheet_name='barnehage')
        barn.to_excel(writer, sheet_name='barn')
        soknad.to_excel(writer, sheet_name='soknad')
        
# --- Diverse hjelpefunksjoner ---
def form_to_object_soknad(sd):
    """sd - formdata for soknad, type: ImmutableMultiDict fra werkzeug.datastructures"""
    foresatt_1 = Foresatt(0,
                          sd.get('navn_forelder_1'),
                          sd.get('adresse_forelder_1'),
                          sd.get('tlf_nr_forelder_1'),
                          sd.get('personnummer_forelder_1'))
    insert_foresatt(foresatt_1)
    foresatt_2 = Foresatt(0,
                          sd.get('navn_forelder_2'),
                          sd.get('adresse_forelder_2'),
                          sd.get('tlf_nr_forelder_2'),
                          sd.get('personnummer_forelder_2'))
    insert_foresatt(foresatt_2) 
    
    foresatt_1.foresatt_id = select_foresatt(sd.get('navn_forelder_1'))
    foresatt_2.foresatt_id = select_foresatt(sd.get('navn_forelder_2'))
    
    barn_1 = Barn(0, sd.get('personnummer_barnet_1'))
    insert_barn(barn_1)
    barn_1.barn_id = select_barn(sd.get('personnummer_barnet_1'))
    
    sok_1 = Soknad(0,
                   foresatt_1,
                   foresatt_2,
                   barn_1,
                   sd.get('fortrinnsrett_barnevern'),
                   sd.get('fortrinnsrett_sykdom_i_familien'),
                   sd.get('fortrinnsrett_sykdome_paa_barnet'),
                   sd.get('fortrinssrett_annet'),
                   sd.get('liste_over_barnehager_prioritert_5'),
                   sd.get('har_sosken_som_gaar_i_barnehagen'),
                   sd.get('tidspunkt_for_oppstart'),
                   sd.get('brutto_inntekt_husholdning'))
    
    return sok_1