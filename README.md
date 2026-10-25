# CG Grants Demo

This project analyzes publicly available data retrieved from a CSV hosted on Coefficient Giving's website that describes its historic grants.

It demonstrates standard data engineering tasks, like data cleaning, preparation, modeling and visualization using CG's data stack.

## Aim

The aim of the analysis is to explore what counts as a renewal for an organization. I've taken a renewal to mean a subsequent grant made to an organization that is closely related to a previous grant. There's no clear definition of how closely related a grant needs to be to count as a renewal.

To explore this, I created a [Streamlit report](https://grant-renewal-demo.streamlit.app) that allows users to explore the data themselves and use parameters to define how similar two grants need to be to count as a renewal.

## My Findings

This dashboard is designed to be experimented with to find a *good definition* of a renewal. New definitions can be created and explored to see which grants fall into each category.

However, to decide which definition is best, or whether a metadata-based definition is even possible, I would need more context about how people refer to renewals and how the term is used at CG. That context would let me propose a definition that mirrors the reality on the ground.

From exploring the data, I don't think a simple metadata-only definition is possible. There are many grants that are independent but look similar, and many renewals that are much larger than the original grant. 

One key issue is that focus area names change over time, so related grants focused on the same area can be categorized as separate. To improve this, I'd seek to understand how focus area names have changed over time, to enable better historical analysis.

While metadata such as amount, date and focus area may not be enough to define renewals, there is rich data in the details column that could be explored further to help inform a definition. Some grants explicitly mention previous grants. Others are clearly focused on the same area. A few techniques could be used here to identify renewals:
- The text of each grant's details could be turned into into embeddings. This would enable the distance between pairs of grants to provide another factor that can help determine whether they are similar enough to count as a renewal.
- LLM analysis could identify cases where the details of a grant explicitly define it as a renewal and identify the previous grant. This could be used as a standalone definition for historic data, or as a source of truth for uncovering other factors closely linked to being a renewal.
- A decision tree model could be built from a human-reviewed set of renewals and non-renewals to identify the factors that are most correlated with being a renewal or not.
- This dataset isn't huge, so reviewing candidate renewals by hand would give the highest quality result. If a permanent improvement to the data was planned, such as always linking grants to their renewals going forward, combining human review with the options above would ensure high quality historic data.
