# coding: utf-8

from io import StringIO
import matplotlib.pyplot as plt
import PIL.Image

explode_ = (0, 0.1, 0, 0)  # only "explode" the 2nd slice (i.e. 'Hogs')


def create_chart(labels=None, sizes=None, colors=None, explode=explode_):
    plt.pie(sizes, explode=explode, labels=labels, colors=colors,
            autopct='%1.1f%%', shadow=True, startangle=90)
    plt.axis('equal')
    return plt


def display_graph(show=True, path=None):
    if path is None:
        path = StringIO()
    canvas = plt.get_current_fig_manager().canvas
    canvas.draw()

    graph_image = PIL.Image.frombytes("RGB", canvas.get_width_height(),
                                      canvas.tostring_rgb())
    graph_image.save(path, 'JPEG')
    plt.close()

    if not show:
        return graph_image
    graph_image.show()
