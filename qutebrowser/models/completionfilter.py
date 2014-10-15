# vim: ft=python fileencoding=utf-8 sts=4 sw=4 et:

# Copyright 2014 Florian Bruhin (The Compiler) <mail@qutebrowser.org>
#
# This file is part of qutebrowser.
#
# qutebrowser is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# qutebrowser is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with qutebrowser.  If not, see <http://www.gnu.org/licenses/>.

"""A filtering/sorting base model for completions.

Contains:
    CompletionFilterModel -- A QSortFilterProxyModel subclass for completions.
"""

from PyQt5.QtCore import QSortFilterProxyModel, QModelIndex

from qutebrowser.models import basecompletion as completion
from qutebrowser.utils import log, qtutils


class CompletionFilterModel(QSortFilterProxyModel):

    """Subclass of QSortFilterProxyModel with custom sorting/filtering.

    Attributes:
        _pattern: The pattern to filter with.
        _srcmodel: The current source model.
                   Kept as attribute because calling `sourceModel` takes quite
                   a long time for some reason.
    """

    def __init__(self, source, parent=None):
        super().__init__(parent)
        super().setSourceModel(source)
        self._srcmodel = source
        self._pattern = ''

    def set_pattern(self, val):
        """Setter for pattern.

        Invalidates the filter and re-sorts the model.

        If the current completion model overrides sort(), it is used.
        If not, the default implementation in QCompletionFilterModel is called.

        Args:
            val: The value to set.
        """
        self._pattern = val
        self.invalidateFilter()
        sortcol = 0
        try:
            self._srcmodel.sort(sortcol)
        except NotImplementedError:
            self.sort(sortcol)
        self.invalidate()

    def count(self):
        """Get the count of non-toplevel items currently visible.

        Note this only iterates one level deep, as we only need root items
        (categories) and children (items) in our model.
        """
        count = 0
        for i in range(self.rowCount()):
            cat = self.index(i, 0)
            qtutils.ensure_valid(cat)
            count += self.rowCount(cat)
        return count

    def first_item(self):
        """Return the first item in the model."""
        for i in range(self.rowCount()):
            cat = self.index(i, 0)
            qtutils.ensure_valid(cat)
            if cat.model().hasChildren(cat):
                index = self.index(0, 0, cat)
                qtutils.ensure_valid(index)
                return index
        return QModelIndex()

    def last_item(self):
        """Return the last item in the model."""
        for i in range(self.rowCount() - 1, -1, -1):
            cat = self.index(i, 0)
            qtutils.ensure_valid(cat)
            if cat.model().hasChildren(cat):
                index = self.index(self.rowCount(cat) - 1, 0, cat)
                qtutils.ensure_valid(index)
                return index
        return QModelIndex()

    def mark_all_items(self, text):
        """Mark the given text in all visible items."""
        for i in range(self.rowCount()):
            cat = self.index(i, 0)
            qtutils.ensure_valid(cat)
            for k in range(self.rowCount(cat)):
                index = self.index(k, 0, cat)
                qtutils.ensure_valid(index)
                index = self.mapToSource(index)
                qtutils.ensure_valid(index)
                self._srcmodel.mark_item(index, text)

    def setSourceModel(self, model):
        """Override QSortFilterProxyModel's setSourceModel to clear pattern."""
        log.completion.debug("Setting source model: {}".format(model))
        self.set_pattern('')
        super().setSourceModel(model)
        self._srcmodel = model

    def filterAcceptsRow(self, row, parent):
        """Custom filter implementation.

        Override QSortFilterProxyModel::filterAcceptsRow.

        Args:
            row: The row of the item.
            parent: The parent item QModelIndex.

        Return:
            True if self._pattern is contained in item, or if it's a root item
            (category). False in all other cases
        """
        if parent == QModelIndex():
            return True
        idx = self._srcmodel.index(row, 0, parent)
        qtutils.ensure_valid(idx)
        data = self._srcmodel.data(idx)
        # TODO more sophisticated filtering
        if not self._pattern:
            return True
        return self._pattern in data

    def lessThan(self, lindex, rindex):
        """Custom sorting implementation.

        Prefers all items which start with self._pattern. Other than that, uses
        normal Python string sorting.

        Args:
            lindex: The QModelIndex of the left item (*left* < right)
            rindex: The QModelIndex of the right item (left < *right*)

        Return:
            True if left < right, else False
        """
        qtutils.ensure_valid(lindex)
        qtutils.ensure_valid(rindex)

        left_sort = self._srcmodel.data(lindex, role=completion.Role.sort)
        right_sort = self._srcmodel.data(rindex, role=completion.Role.sort)

        if left_sort is not None and right_sort is not None:
            return left_sort < right_sort

        left = self._srcmodel.data(lindex)
        right = self._srcmodel.data(rindex)

        leftstart = left.startswith(self._pattern)
        rightstart = right.startswith(self._pattern)

        if leftstart and rightstart:
            return left < right
        elif leftstart:
            return True
        elif rightstart:
            return False
        else:
            return left < right
