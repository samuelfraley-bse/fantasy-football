from espn_api.football import League

league = League(
    league_id=31028552,
    year=2025,
    swid="{268DF5A5-4649-40C0-8DF5-A54649A0C071}",
    espn_s2="AEC5tO5I9Z%2BJNFGF0zrEvLGm98e%2BR805ciFrlH%2BwmA4WCi0Z7bgJhp2i1gch5cG4dmkgaKlSTBgjnpThqxB2P7ikv9pcyxkcuLJ8fCLAXChgdhan6sp5TXui1tiH839g5JuC1LT5nIC0wNqi6zjo1dwSX2tv1TcdEtTiul8Z4067w%2F%2FysP%2FNXPJQPc2mWXN6IqIMrSjOiPPxKRN1Qce3BHDLcZWIN%2FtBerzOXqPlr3MSuBpFZceV5DvBsZ4OjFHH8986ATpCNRJlkCP3MDjV7NYuZI22ADKZEQvCwZaRy28u9g%3D%3D"
)

print("League name:", league.settings.name)
print("Teams:")
for team in league.teams:
    print("-", team.team_name)
