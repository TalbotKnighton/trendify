import matplotlib.pyplot as plt

from dataclasses import dataclass


@dataclass
class Coordinate:
    xyz = tuple[float, float, float]


def main():
    coords = [
        [(-1681, 52, -1274), (-2377, 62, -967), (2996, 67, 2797), (-238, 69, -211)],
        [(2295, 73, -514), (1490, 70, -1091), (265, 60, -836), (-1061, 63, 217)],
        [(-70, 63, -926), (2107, 60, 2934), (1223, 61, 1574), (-954, 74, 579)],
        [(-2196, 58, -1390), (917, 77, -907), (1167, 70, -2741), (49, 51, 758)],
        [(251, 54, -1118), (1858, 75, -2807), (-128, 52, 1605), (-2144, 60, 971)],
    ]
    flattened_list = []
    for sublist in coords:
        for item in sublist:
            flattened_list.append(item)
    coords = flattened_list

    fig, ax = plt.subplots()

    for coord in coords:
        ax.scatter(x=coord[0], y=coord[2])

    min_x = min([x[0] for x in coords])
    max_x = max([x[0] for x in coords])
    min_z = min([x[2] for x in coords])
    max_z = max([x[2] for x in coords])
    fig.show()
    breakpoint()


if __name__ == "__main__":
    main()
