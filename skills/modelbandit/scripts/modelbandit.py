"""Rank OpenRouter models by domain popularity and price them live.

Stdlib only. Reads OpenRouter's task-classification leaderboards and daily token
rankings (Data API; CC BY 4.0), maps them to a domain from policy.json, and
emits a popularity-ranked candidate table priced at live rates, with effort
rungs and a batch cost projection. Prices are per-endpoint, not the models-list
figure: the same model can span 20x on output across providers, so projection
defaults to the worst endpoint. Mechanics live in --help; SKILL.md holds the
policy.
"""


# The implementation lives in the modelbandit package beside this file; this
# script stays the invoked entry point, so every doc reference and deployment
# shape keeps working. Running it imports the package and dispatches to main.
if __name__ == "__main__":
    from modelbandit import main
    main()
