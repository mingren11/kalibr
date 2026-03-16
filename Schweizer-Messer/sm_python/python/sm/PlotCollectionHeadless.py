# Headless PlotCollection: no wx/matplotlib GUI, for --dont-show-report / embedded use.
# Same interface as PlotCollection: add_figure(), show() (no-op).
import collections

class PlotCollection:
    """Stub when wx is not available: collects figures but show() is no-op."""
    def __init__(self, window_name="", window_size=(800, 600)):
        self.frame_name = window_name
        self.window_size = window_size
        self.figureList = collections.OrderedDict()

    def add_figure(self, tabname, fig):
        self.figureList[tabname] = fig

    def delete_figure(self, name):
        self.figureList.pop(name, None)

    def show(self):
        pass  # no-op: no display
