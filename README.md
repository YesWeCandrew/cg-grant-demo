# CG Grants Demo

This project analyses publically available data retrieved from a CSV hosted on Coefficient Giving's website that describes it's historic grants.

It demonstrates standard data engineering tasks, like data cleaning, preparation, modelling and visualisation using CG's data stack.

## Aim

The aim of the analysis is to explore what counts as a renewal for an organization. I've taken a renewal to mean a subsequent grant made to an organization to that is closely related to a previous grant. I don't have a clear definition of how 'closely related' a grant needs to be to count as a renewal.

To explore this, I created a [streamlit report](https://grant-renewal-demo.streamlit.app) that allows users to explore the data themselves and use parameters to define how similar two grants need to be to count as a renewal.

## My Findings

This dashboard is designed to be experimented with. New definitions can be created and then explored to determine which grants fall into each category.

However, for me to define which definition is best (or if a metadata based definition is even possible) I need a lot more context and understanding about how people refer to renewals and how the term is used at CG. This context would enable me to create a proposed definition that mirrors the reality on the ground.

From exploring the data, I don't think a simple-metadata only definition will be possible. Their are many grants that are independent but look similar, and many renewals much larger than the original grant. 

One key issue is the changing of focus area names over time. This results in grants that are related and focused on the same area being categorised as seperate. To improve this, I would seek to understand how the names of focus areas has changed over time, to enable better historical analysis.

While the metadata details like amount, date and focus area may not be enough to define renewals, their is rich and significant data in the details column that could be explored further to help inform a definition. Some grants explicitly mention that they refer to previous grants. Others are clearly focused on the same area. Some machine learning techniques could be adopted here to identify renewals:
- Text could be transformed into embeddings and the distance between pairs of related grants could be used to determine if the grants are reasonably similar enough to be counted as a renewal.
- LLM analysis could identify cases where the details of a grant explicitly define it as a renewal and identify the previous grant. This identification could be used as a standalone definition for historic data, or used as a source of truth to enable further investigations that can uncover the other factors that are highly correlated with being an explicit renewal.
- Another option would be to use a human reviewed set of renewals and non renewals, and use decision tree analysis to build a categorization model.
- One final option: This data set isn't huge. Human review of candidate renewals would be the highest quality result. If a permenant improvement to the data was planned, such as linking grants to any renewals, human review combined with the options above would be a wise move to ensure high quality results for historic data.


