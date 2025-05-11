import trendify as tdy

tdy.AssetSpecs.add_spec(
    spec=tdy.FigSpec(
        tag='',
        title='myfigtitle',
    )
)
print(tdy.AssetSpecs.model_dump())