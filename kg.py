from flask import Flask, url_for, render_template, request, redirect, session
import pandas as pd
import altair as alt

from kgcontroller import (form_to_object_soknad, insert_soknad, commit_all, select_alle_barnehager, select_alle_soknader)

app = Flask(__name__)  # Corrected to _name_
app.secret_key = 'BAD_SECRET_KEY'  # necessary for session


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/barnehager')
def barnehager():
    information = select_alle_barnehager()
    return render_template('barnehager.html', data=information)


@app.route('/behandle', methods=['GET', 'POST'])
def behandle():
    if request.method == 'POST':
        sd = request.form
        soknad_objekt = form_to_object_soknad(sd)
        insert_soknad(soknad_objekt)
        commit_all()
        session['information'] = sd

        ledige_plasser = 5
        status = "AVSLAG"

        if ledige_plasser > 0:
            status = "TILBUD"
        elif (sd.get('fortrinnsrett_barnevern') or 
              sd.get('fortrinnsrett_sykdom_i_familien') or 
              sd.get('fortrinnsrett_sykdome_paa_barnet')):
            status = "Fortrinnsrett, venter på ledig plass"

        return render_template('svar.html', data=sd, status=status)
    else:
        return render_template('soknad.html')


@app.route('/svar')
def svar():
    if 'information' in session:
        information = session['information']
        status = "AVSLAG"
        return render_template('svar.html', data=information, status=status)
    else:
        return redirect(url_for('index'))

@app.route('/commit')
def commit():
    commit_all()
    data_path = 'kgdata.xlsx'
    try:
        # Use openpyxl as the engine to read Excel files
        foresatte_df = pd.read_excel(data_path, sheet_name='foresatt', engine='openpyxl')
        barn_df = pd.read_excel(data_path, sheet_name='barn', engine='openpyxl')
        soknad_df = pd.read_excel(data_path, sheet_name='soknad', engine='openpyxl')
    except FileNotFoundError:
        return "Feil: Excel-filen 'kgdata.xlsx' ble ikke funnet."
    except Exception as e:
        return f"Feil ved lesing av Excel-filen: {e}"

    return render_template('commit.html', foresatte=foresatte_df.to_dict(orient='records'),
                           barn=barn_df.to_dict(orient='records'),
                           soknader=soknad_df.to_dict(orient='records'))




@app.route('/soeknader')
def soeknader():
    alle_soknader = select_alle_soknader()
    ledige_plasser = 5

    for soknad in alle_soknader:
        # Assign "TILBUD" or "Fortrinnsrett, venter på ledig plass" based on conditions
        if ledige_plasser > 0:
            soknad.status = "TILBUD"
            ledige_plasser -= 1
        elif soknad.fr_barnevern or soknad.fr_sykd_familie or soknad.fr_sykd_barn:
            soknad.status = "Fortrinnsrett, venter på ledig plass"
        else:
            soknad.status = "AVSLAG"

    return render_template('soeknader.html', soknader=alle_soknader)

@app.route('/statistikk', methods=['GET', 'POST'])
def statistikk():
    data_path = 'ssb-barnehager-2015-2023-alder-1-2-aar.xlsm'
    try:
        # Use openpyxl engine to read the Excel file
        df = pd.read_excel(data_path, sheet_name='KOSandel120000', engine='openpyxl')
        
        # Clean the data by skipping initial rows without useful data and renaming columns
        df.columns = df.iloc[2]  # Set the header row to row index 2
        df = df[3:]  # Skip the first few rows that do not contain actual data
        df.rename(columns={df.columns[0]: "Kommune"}, inplace=True)
        df.dropna(axis=1, how='all', inplace=True)  # Drop columns that are entirely NaN
        
    except FileNotFoundError:
        return "Feil: Excel-filen 'ssb-barnehager-2015-2023-alder-1-2-aar.xlsm' ble ikke funnet."
    except Exception as e:
        return f"Feil ved lesing av Excel-filen: {e}"

    if request.method == 'POST':
        valgt_kommune = request.form.get('kommune')
        df_kommune = df[df['Kommune'] == valgt_kommune]

        try:
            headers = [str(year) for year in range(2015, 2024) if str(year) in df_kommune.columns]
            df_kommune_melted = df_kommune.melt(id_vars=['Kommune'], value_vars=headers, var_name='Year', value_name='Percentage')

            chart = alt.Chart(df_kommune_melted).mark_line(point=True).encode(
                x=alt.X('Year:O', title='Year'),
                y=alt.Y('Percentage:Q', title='Percentage in Kindergarten'),
                tooltip=['Year', 'Percentage']
            ).properties(
                title=f'Kindergarten Enrollment Percentage for {valgt_kommune} (2015-2023)',
                width=600,
                height=400
            )

            chart_path = f'static/{valgt_kommune}_kindergarten_chart.html'
            chart.save(chart_path)
            return render_template('statistikk.html', chart_path=chart_path, kommuner=df['Kommune'].unique())
        
        except ValueError as e:
            return f"Error while creating the chart: {e}"

    return render_template('statistikk.html', kommuner=df['Kommune'].unique())


if __name__ == "__main__":
    app.run(debug=False)
