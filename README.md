# CG Grants Demo

This project analyses publically available data from CG on historic grants, retrieved from https://coefficientgiving.org/wp-content/uploads/Coefficient-Giving-Grants-Archive.csv.

It demonstrates standard data engineering tasks, like data cleaning, preparation, modelling and visualisation using CG's data stack.

## Aim

The aim of the analysis is to explore what counts as a renewal for a grant. A renewal is ambiguously described as when a grant is made for a subsequent time, but there is no clear indicator of this.

To explore this, I'll create a streamlit report that allows users to explore the data themselves and use parameters to define the time period (or potentially similarity in amount) that defines a renewal.