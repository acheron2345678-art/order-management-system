document.addEventListener("DOMContentLoaded", () => {

    const table =
        document.getElementById("ordersTable");

    if (!table) {
        return;
    }


    if (typeof DataTable === "undefined") {

        console.error(
            "DataTables v2 is not loaded."
        );

        return;
    }


    if (
        DataTable.isDataTable(
            "#ordersTable"
        )
    ) {
        return;
    }


    const dataTable =
        new DataTable(
            "#ordersTable",
            {

                paging: true,

                ordering: {
                    indicator: true,
                    handler: true,
                },

                searching: true,

                info: true,

                processing: false,

                pageLength: 10,

                lengthMenu: [
                    10,
                    25,
                    50,
                    100
                ],


                order: [
                    [7, "desc"],
                    [0, "desc"]
                ],


                scrollX: true,

                autoWidth: false,


                columnDefs: [

                    {
                        targets: 0,
                        type: "num",
                    },

                    {
                        targets: 5,
                        type: "num",
                    },

                    {
                        targets: 7,
                        type: "date",
                    },

                    {
                        targets: -1,
                        orderable: false,
                        searchable: false,
                    },

                ],


                layout: {

                    topStart:
                        "pageLength",

                    topEnd:
                        "search",

                    bottomStart:
                        "info",

                    bottomEnd:
                        "paging",

                },


                language: {

                    search:
                        "Search table:",

                    searchPlaceholder:
                        "Search these orders...",

                    lengthMenu:
                        "Show _MENU_ orders",

                    info:
                        "Showing _START_ to _END_ of _TOTAL_ orders",

                    infoEmpty:
                        "Showing 0 to 0 of 0 orders",

                    emptyTable:
                        "No orders found",

                    zeroRecords:
                        "No matching orders found",

                    paginate: {

                        first:
                            "First",

                        previous:
                            "Previous",

                        next:
                            "Next",

                        last:
                            "Last",

                    },

                },

            }
        );


    table
        .querySelectorAll(
            "thead th"
        )
        .forEach(
            (
                header,
                index
            ) => {

                if (index !== 7) {

                    header
                        .classList
                        .add(
                            "sortable-column"
                        );

                    header.title =
                        "Click to sort";

                }

            }
        );


    requestAnimationFrame(
        () => {

            dataTable
                .columns
                .adjust();

        }
    );

});