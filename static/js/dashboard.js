(() => {

    let dashboardData = null;

    let selectedMetric =
        "completed";

    let selectedProductMetric =
        "quantity";

    let resizeTimer = null;


    const metricConfig = {

        total: {
            label: "Orders",
            currency: false
        },

        pending: {
            label: "Pending",
            currency: false
        },

        processing: {
            label: "Processing",
            currency: false
        },

        completed: {
            label: "Completed",
            currency: false
        },

        cancelled: {
            label: "Cancelled",
            currency: false
        },

        amount: {
            label: "Revenue",
            currency: true
        }

    };


    function cssVar(
        name,
        fallback
    ) {

        const value =
            getComputedStyle(
                document.documentElement
            )
            .getPropertyValue(
                name
            )
            .trim();

        return (
            value
            ||
            fallback
        );

    }


    function chartColors() {

        return {

            text:
                cssVar(
                    "--bs-emphasis-color",
                    "#212529"
                ),

            muted:
                cssVar(
                    "--bs-secondary-color",
                    "#6c757d"
                ),

            border:
                cssVar(
                    "--bs-border-color",
                    "#dee2e6"
                ),

            surface:
                cssVar(
                    "--bs-body-bg",
                    "#ffffff"
                ),

            primary:
                cssVar(
                    "--bs-primary",
                    "#0d6efd"
                ),

            swiggy:
                cssVar(
                    "--om-swiggy",
                    "#fc8019"
                ),

            insights:
                cssVar(
                    "--om-insights",
                    "#4f6bed"
                ),

            combined:
                cssVar(
                    "--om-combined",
                    "#7c3aed"
                )

        };

    }


    function escapeHtml(
        value
    ) {

        const div =
            document.createElement(
                "div"
            );

        div.textContent =
            value ?? "";

        return div.innerHTML;

    }


    function formatNumber(
        value
    ) {

        return Number(
            value || 0
        ).toLocaleString(
            "en-IN"
        );

    }


    function formatCurrency(
        value
    ) {

        return (
            "₹"
            +
            Number(
                value || 0
            ).toLocaleString(
                "en-IN",
                {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                }
            )
        );

    }


    function formatMetric(
        value
    ) {

        if (
            metricConfig[
                selectedMetric
            ].currency
        ) {

            return formatCurrency(
                value
            );

        }

        return formatNumber(
            value
        );

    }


    function formatDate(
        dateValue
    ) {

        if (!dateValue) {
            return "—";
        }

        const currentDate =
            new Date(
                `${dateValue}T00:00:00Z`
            );

        return (
            new Intl.DateTimeFormat(
                "en-IN",
                {
                    day: "numeric",
                    month: "short",
                    timeZone: "UTC"
                }
            )
            .format(
                currentDate
            )
        );

    }


    function formatFullDate(
        dateValue
    ) {

        if (!dateValue) {
            return "—";
        }

        const currentDate =
            new Date(
                `${dateValue}T00:00:00Z`
            );

        return (
            new Intl.DateTimeFormat(
                "en-IN",
                {
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                    timeZone: "UTC"
                }
            )
            .format(
                currentDate
            )
        );

    }


    function axisTickDates(
        data,
        maxTicks = 5
    ) {

        if (
            data.length
            <= maxTicks
        ) {

            return data.map(
                item =>
                    item.date
            );

        }

        const step =
            Math.ceil(
                data.length
                /
                maxTicks
            );

        return data
            .filter(
                (
                    _,
                    index
                ) =>
                    (
                        index
                        %
                        step
                    )
                    === 0
                    ||
                    index
                    ===
                    data.length - 1
            )
            .map(
                item =>
                    item.date
            );

    }


    function axisValue(
        value
    ) {

        if (
            selectedMetric
            === "amount"
        ) {

            if (
                Number(
                    value
                )
                >=
                1000
            ) {

                return (
                    "₹"
                    +
                    d3.format(
                        ".2~s"
                    )(
                        value
                    )
                );

            }

            return (
                "₹"
                +
                value
            );

        }

        return d3.format(
            "~g"
        )(
            value
        );

    }


    function summaryHelper(
        platformData,
        platformName
    ) {

        if (
            selectedMetric
            === "amount"
        ) {

            return (
                "Completed revenue"
            );

        }

        if (
            selectedMetric
            === "total"
        ) {

            return (
                `All ${platformName} orders`
            );

        }

        const total =
            Number(
                platformData.total
                ||
                0
            );

        const value =
            Number(
                platformData[
                    selectedMetric
                ]
                ||
                0
            );

        if (!total) {

            return (
                "No orders yet"
            );

        }

        return (
            (
                value
                /
                total
                *
                100
            ).toFixed(
                1
            )
            +
            `% of ${platformName} orders`
        );

    }


    function updateSummary(
        prefix,
        platformData,
        platformName
    ) {

        const label =
            document.getElementById(
                `${prefix}-metric-label`
            );

        const value =
            document.getElementById(
                `${prefix}-metric-value`
            );

        const helper =
            document.getElementById(
                `${prefix}-metric-helper`
            );


        if (label) {

            label.textContent =
                metricConfig[
                    selectedMetric
                ].label;

        }


        if (value) {

            value.textContent =
                formatMetric(
                    platformData[
                        selectedMetric
                    ]
                );

        }


        if (helper) {

            helper.textContent =
                summaryHelper(
                    platformData,
                    platformName
                );

        }

    }


    function updateAnalysisSummaries() {

        updateSummary(
            "swiggy",
            dashboardData.swiggy,
            "Swiggy"
        );

        updateSummary(
            "insights",
            dashboardData.insights,
            "Insights"
        );


        const combinedLabel =
            document.getElementById(
                "combined-metric-label"
            );

        const combinedValue =
            document.getElementById(
                "combined-metric-value"
            );

        const combinedHelper =
            document.getElementById(
                "combined-metric-helper"
            );


        if (combinedLabel) {

            combinedLabel.textContent =
                metricConfig[
                    selectedMetric
                ].label;

        }


        if (combinedValue) {

            combinedValue.textContent =
                formatMetric(
                    dashboardData
                        .combined[
                            selectedMetric
                        ]
                );

        }


        if (combinedHelper) {

            combinedHelper.textContent =
                selectedMetric
                ===
                "amount"
                    ?
                    "Completed revenue across both platforms"
                    :
                    "Swiggy + Insights";

        }

    }


    function prepareChart(
        containerId,
        height
    ) {

        const container =
            document.getElementById(
                containerId
            );

        if (!container) {

            return null;

        }

        container.innerHTML =
            "";

        const width =
            Math.max(
                container.clientWidth,
                260
            );

        const svg =
            d3
                .select(
                    container
                )
                .append(
                    "svg"
                )
                .attr(
                    "viewBox",
                    `0 0 ${width} ${height}`
                )
                .attr(
                    "width",
                    "100%"
                )
                .attr(
                    "height",
                    height
                )
                .attr(
                    "preserveAspectRatio",
                    "xMidYMid meet"
                );

        return {
            container,
            svg,
            width,
            height
        };

    }


    function showEmpty(
        container,
        message
    ) {

        container.innerHTML =
            `
            <div class="dashboard-empty-state">
                ${escapeHtml(message)}
            </div>
            `;

    }


    function makeTooltip(
        container
    ) {

        return d3
            .select(
                container
            )
            .append(
                "div"
            )
            .attr(
                "class",
                "dashboard-chart-tooltip"
            )
            .style(
                "display",
                "none"
            );

    }


    function moveTooltip(
        tooltip,
        container,
        event
    ) {

        const bounds =
            container
                .getBoundingClientRect();

        let left =
            event.clientX
            -
            bounds.left
            +
            14;

        let top =
            event.clientY
            -
            bounds.top
            -
            74;

        left =
            Math.max(
                8,
                Math.min(
                    left,
                    bounds.width
                    -
                    200
                )
            );

        top =
            Math.max(
                8,
                top
            );

        tooltip
            .style(
                "left",
                `${left}px`
            )
            .style(
                "top",
                `${top}px`
            );

    }


    function drawPlatformTrend(
        containerId,
        trend,
        color,
        platform
    ) {

        const prepared =
            prepareChart(
                containerId,
                250
            );

        if (!prepared) {

            return;

        }

        const {
            container,
            svg,
            width,
            height
        } = prepared;


        if (
            !trend
            ||
            trend.length
            === 0
        ) {

            showEmpty(
                container,
                "No trend data available yet."
            );

            return;

        }


        const colors =
            chartColors();


        const margin = {
            top: 18,
            right: 12,
            bottom: 38,
            left: 46
        };


        const innerWidth =
            width
            -
            margin.left
            -
            margin.right;


        const innerHeight =
            height
            -
            margin.top
            -
            margin.bottom;


        const values =
            trend.map(
                item => ({
                    ...item,

                    value:
                        Number(
                            item[
                                selectedMetric
                            ]
                            ||
                            0
                        )
                })
            );


        const x =
            d3
                .scalePoint()
                .domain(
                    values.map(
                        item =>
                            item.date
                    )
                )
                .range(
                    [
                        0,
                        innerWidth
                    ]
                )
                .padding(
                    0.35
                );


        const maxValue =
            d3.max(
                values,
                item =>
                    item.value
            )
            ||
            0;


        const y =
            d3
                .scaleLinear()
                .domain(
                    [
                        0,
                        maxValue
                        ===
                        0
                            ?
                            1
                            :
                            maxValue
                            *
                            1.2
                    ]
                )
                .nice()
                .range(
                    [
                        innerHeight,
                        0
                    ]
                );


        const group =
            svg
                .append(
                    "g"
                )
                .attr(
                    "transform",
                    `translate(${margin.left},${margin.top})`
                );


        group
            .append(
                "g"
            )
            .call(
                d3
                    .axisLeft(
                        y
                    )
                    .ticks(
                        4
                    )
                    .tickSize(
                        -innerWidth
                    )
                    .tickFormat(
                        axisValue
                    )
            )
            .call(
                axis =>
                    axis
                        .select(
                            ".domain"
                        )
                        .remove()
            )
            .call(
                axis =>
                    axis
                        .selectAll(
                            ".tick line"
                        )
                        .attr(
                            "stroke",
                            colors.border
                        )
                        .attr(
                            "stroke-opacity",
                            0.45
                        )
            )
            .call(
                axis =>
                    axis
                        .selectAll(
                            ".tick text"
                        )
                        .attr(
                            "fill",
                            colors.muted
                        )
                        .attr(
                            "font-size",
                            10
                        )
            );


        group
            .append(
                "g"
            )
            .attr(
                "transform",
                `translate(0,${innerHeight})`
            )
            .call(
                d3
                    .axisBottom(
                        x
                    )
                    .tickValues(
                        axisTickDates(
                            values,
                            width
                            <
                            420
                                ?
                                3
                                :
                                5
                        )
                    )
                    .tickSize(
                        0
                    )
                    .tickFormat(
                        formatDate
                    )
            )
            .call(
                axis =>
                    axis
                        .select(
                            ".domain"
                        )
                        .remove()
            )
            .call(
                axis =>
                    axis
                        .selectAll(
                            ".tick text"
                        )
                        .attr(
                            "fill",
                            colors.muted
                        )
                        .attr(
                            "font-size",
                            10
                        )
                        .attr(
                            "dy",
                            "1.25em"
                        )
            );


        const gradientId =
            `gradient-${containerId}`;


        const gradient =
            svg
                .append(
                    "defs"
                )
                .append(
                    "linearGradient"
                )
                .attr(
                    "id",
                    gradientId
                )
                .attr(
                    "x1",
                    "0%"
                )
                .attr(
                    "y1",
                    "0%"
                )
                .attr(
                    "x2",
                    "0%"
                )
                .attr(
                    "y2",
                    "100%"
                );


        gradient
            .append(
                "stop"
            )
            .attr(
                "offset",
                "0%"
            )
            .attr(
                "stop-color",
                color
            )
            .attr(
                "stop-opacity",
                0.24
            );


        gradient
            .append(
                "stop"
            )
            .attr(
                "offset",
                "100%"
            )
            .attr(
                "stop-color",
                color
            )
            .attr(
                "stop-opacity",
                0
            );


        const line =
            d3
                .line()
                .x(
                    item =>
                        x(
                            item.date
                        )
                )
                .y(
                    item =>
                        y(
                            item.value
                        )
                )
                .curve(
                    d3.curveMonotoneX
                );


        const area =
            d3
                .area()
                .x(
                    item =>
                        x(
                            item.date
                        )
                )
                .y0(
                    innerHeight
                )
                .y1(
                    item =>
                        y(
                            item.value
                        )
                )
                .curve(
                    d3.curveMonotoneX
                );


        group
            .append(
                "path"
            )
            .datum(
                values
            )
            .attr(
                "fill",
                `url(#${gradientId})`
            )
            .attr(
                "d",
                area
            );


        group
            .append(
                "path"
            )
            .datum(
                values
            )
            .attr(
                "fill",
                "none"
            )
            .attr(
                "stroke",
                color
            )
            .attr(
                "stroke-width",
                3
            )
            .attr(
                "stroke-linecap",
                "round"
            )
            .attr(
                "stroke-linejoin",
                "round"
            )
            .attr(
                "d",
                line
            );


        const tooltip =
            makeTooltip(
                container
            );


        const points =
            group
                .selectAll(
                    ".dashboard-point"
                )
                .data(
                    values
                )
                .join(
                    "g"
                )
                .attr(
                    "class",
                    "dashboard-point"
                )
                .attr(
                    "transform",
                    item =>
                        `translate(${x(item.date)},${y(item.value)})`
                )
                .style(
                    "cursor",
                    "pointer"
                );


        points
            .append(
                "circle"
            )
            .attr(
                "r",
                13
            )
            .attr(
                "fill",
                "transparent"
            );


        points
            .append(
                "circle"
            )
            .attr(
                "class",
                "dashboard-point-dot"
            )
            .attr(
                "r",
                4.5
            )
            .attr(
                "fill",
                color
            )
            .attr(
                "stroke",
                colors.surface
            )
            .attr(
                "stroke-width",
                3
            );


        points
            .on(
                "mouseenter",
                function (
                    event,
                    item
                ) {

                    d3
                        .select(
                            this
                        )
                        .select(
                            ".dashboard-point-dot"
                        )
                        .attr(
                            "r",
                            7
                        );

                    tooltip
                        .style(
                            "display",
                            "block"
                        )
                        .html(
                            `
                            <strong>
                                ${formatFullDate(item.date)}
                            </strong>

                            <span>
                                ${metricConfig[selectedMetric].label}:
                                ${formatMetric(item.value)}
                            </span>

                            <small>
                                Click to inspect orders
                            </small>
                            `
                        );

                }
            )
            .on(
                "mousemove",
                event => {

                    moveTooltip(
                        tooltip,
                        container,
                        event
                    );

                }
            )
            .on(
                "mouseleave",
                function () {

                    d3
                        .select(
                            this
                        )
                        .select(
                            ".dashboard-point-dot"
                        )
                        .attr(
                            "r",
                            4.5
                        );

                    tooltip.style(
                        "display",
                        "none"
                    );

                }
            )
            .on(
                "click",
                (
                    event,
                    item
                ) => {

                    tooltip.style(
                        "display",
                        "none"
                    );

                    openDrilldown(
                        platform,
                        item.date
                    );

                }
            );

    }


    function drawCombinedComparison() {

        const prepared =
            prepareChart(
                "combined-dashboard-chart",
                285
            );

        if (!prepared) {

            return;

        }

        const {
            container,
            svg,
            width,
            height
        } = prepared;


        const swiggyTrend =
            dashboardData
                .swiggy
                .trend
            ||
            [];


        const insightsTrend =
            dashboardData
                .insights
                .trend
            ||
            [];


        if (
            swiggyTrend.length
            === 0
            &&
            insightsTrend.length
            === 0
        ) {

            showEmpty(
                container,
                "No comparison data available yet."
            );

            return;

        }


        const colors =
            chartColors();


        const margin = {
            top: 18,
            right: 18,
            bottom: 40,
            left: 50
        };


        const innerWidth =
            width
            -
            margin.left
            -
            margin.right;


        const innerHeight =
            height
            -
            margin.top
            -
            margin.bottom;


        const comparison =
            swiggyTrend.map(
                (
                    item,
                    index
                ) => ({

                    date:
                        item.date,

                    swiggy:
                        Number(
                            item[
                                selectedMetric
                            ]
                            ||
                            0
                        ),

                    insights:
                        Number(
                            insightsTrend[
                                index
                            ]?.[
                                selectedMetric
                            ]
                            ||
                            0
                        )

                })
            );


        const x =
            d3
                .scalePoint()
                .domain(
                    comparison.map(
                        item =>
                            item.date
                    )
                )
                .range(
                    [
                        0,
                        innerWidth
                    ]
                )
                .padding(
                    0.28
                );


        const maxValue =
            d3.max(
                comparison,
                item =>
                    Math.max(
                        item.swiggy,
                        item.insights
                    )
            )
            ||
            0;


        const y =
            d3
                .scaleLinear()
                .domain(
                    [
                        0,
                        maxValue
                        ===
                        0
                            ?
                            1
                            :
                            maxValue
                            *
                            1.18
                    ]
                )
                .nice()
                .range(
                    [
                        innerHeight,
                        0
                    ]
                );


        const group =
            svg
                .append(
                    "g"
                )
                .attr(
                    "transform",
                    `translate(${margin.left},${margin.top})`
                );


        group
            .append(
                "g"
            )
            .call(
                d3
                    .axisLeft(
                        y
                    )
                    .ticks(
                        4
                    )
                    .tickSize(
                        -innerWidth
                    )
                    .tickFormat(
                        axisValue
                    )
            )
            .call(
                axis =>
                    axis
                        .select(
                            ".domain"
                        )
                        .remove()
            )
            .call(
                axis =>
                    axis
                        .selectAll(
                            ".tick line"
                        )
                        .attr(
                            "stroke",
                            colors.border
                        )
                        .attr(
                            "stroke-opacity",
                            0.4
                        )
            )
            .call(
                axis =>
                    axis
                        .selectAll(
                            ".tick text"
                        )
                        .attr(
                            "fill",
                            colors.muted
                        )
                        .attr(
                            "font-size",
                            10
                        )
            );


        group
            .append(
                "g"
            )
            .attr(
                "transform",
                `translate(0,${innerHeight})`
            )
            .call(
                d3
                    .axisBottom(
                        x
                    )
                    .tickValues(
                        axisTickDates(
                            comparison,
                            width
                            <
                            620
                                ?
                                4
                                :
                                6
                        )
                    )
                    .tickSize(
                        0
                    )
                    .tickFormat(
                        formatDate
                    )
            )
            .call(
                axis =>
                    axis
                        .select(
                            ".domain"
                        )
                        .remove()
            )
            .call(
                axis =>
                    axis
                        .selectAll(
                            ".tick text"
                        )
                        .attr(
                            "fill",
                            colors.muted
                        )
                        .attr(
                            "font-size",
                            10
                        )
                        .attr(
                            "dy",
                            "1.25em"
                        )
            );


        const series = [

            {
                key: "swiggy",
                color:
                    colors.swiggy
            },

            {
                key: "insights",
                color:
                    colors.insights
            }

        ];


        series.forEach(
            seriesItem => {

                const line =
                    d3
                        .line()
                        .x(
                            item =>
                                x(
                                    item.date
                                )
                        )
                        .y(
                            item =>
                                y(
                                    item[
                                        seriesItem.key
                                    ]
                                )
                        )
                        .curve(
                            d3.curveMonotoneX
                        );


                group
                    .append(
                        "path"
                    )
                    .datum(
                        comparison
                    )
                    .attr(
                        "fill",
                        "none"
                    )
                    .attr(
                        "stroke",
                        seriesItem.color
                    )
                    .attr(
                        "stroke-width",
                        3
                    )
                    .attr(
                        "stroke-linecap",
                        "round"
                    )
                    .attr(
                        "stroke-linejoin",
                        "round"
                    )
                    .attr(
                        "d",
                        line
                    );

            }
        );


        const tooltip =
            makeTooltip(
                container
            );


        const pointGroups =
            group
                .selectAll(
                    ".combined-date-point"
                )
                .data(
                    comparison
                )
                .join(
                    "g"
                )
                .attr(
                    "class",
                    "combined-date-point"
                )
                .style(
                    "cursor",
                    "pointer"
                );


        pointGroups
            .append(
                "rect"
            )
            .attr(
                "x",
                item =>
                    x(
                        item.date
                    )
                    -
                    14
            )
            .attr(
                "y",
                0
            )
            .attr(
                "width",
                28
            )
            .attr(
                "height",
                innerHeight
            )
            .attr(
                "fill",
                "transparent"
            );


        pointGroups.each(
            function (
                item
            ) {

                const point =
                    d3.select(
                        this
                    );


                point
                    .append(
                        "circle"
                    )
                    .attr(
                        "cx",
                        x(
                            item.date
                        )
                    )
                    .attr(
                        "cy",
                        y(
                            item.swiggy
                        )
                    )
                    .attr(
                        "r",
                        4
                    )
                    .attr(
                        "fill",
                        colors.swiggy
                    )
                    .attr(
                        "stroke",
                        colors.surface
                    )
                    .attr(
                        "stroke-width",
                        2.5
                    );


                point
                    .append(
                        "circle"
                    )
                    .attr(
                        "cx",
                        x(
                            item.date
                        )
                    )
                    .attr(
                        "cy",
                        y(
                            item.insights
                        )
                    )
                    .attr(
                        "r",
                        4
                    )
                    .attr(
                        "fill",
                        colors.insights
                    )
                    .attr(
                        "stroke",
                        colors.surface
                    )
                    .attr(
                        "stroke-width",
                        2.5
                    );

            }
        );


        pointGroups
            .on(
                "mouseenter",
                (
                    event,
                    item
                ) => {

                    const total =
                        item.swiggy
                        +
                        item.insights;


                    tooltip
                        .style(
                            "display",
                            "block"
                        )
                        .html(
                            `
                            <strong>
                                ${formatFullDate(item.date)}
                            </strong>

                            <span>
                                Swiggy:
                                ${formatMetric(item.swiggy)}
                            </span>

                            <span>
                                Insights:
                                ${formatMetric(item.insights)}
                            </span>

                            <span>
                                Combined:
                                ${formatMetric(total)}
                            </span>

                            <small>
                                Click to inspect orders
                            </small>
                            `
                        );

                }
            )
            .on(
                "mousemove",
                event => {

                    moveTooltip(
                        tooltip,
                        container,
                        event
                    );

                }
            )
            .on(
                "mouseleave",
                () => {

                    tooltip.style(
                        "display",
                        "none"
                    );

                }
            )
            .on(
                "click",
                (
                    event,
                    item
                ) => {

                    tooltip.style(
                        "display",
                        "none"
                    );

                    openDrilldown(
                        "combined",
                        item.date
                    );

                }
            );

    }


    function normalizeProductControls() {

        document
            .querySelectorAll(
                ".dashboard-product-btn"
            )
            .forEach(
                button => {

                    if (
                        button
                            .dataset
                            .productMetric
                        ===
                        "orders"
                    ) {

                        button
                            .dataset
                            .productMetric =
                            "quantity";


                        const currentText =
                            button
                                .textContent
                                .trim()
                                .toLowerCase();


                        if (
                            currentText.includes(
                                "order"
                            )
                        ) {

                            button.textContent =
                                "Units Sold";

                        }

                    }

                }
            );

    }


    function updateProductDescription() {

        const description =
            document.getElementById(
                "product-chart-description"
            );

        if (!description) {

            return;

        }

        if (
            selectedProductMetric
            ===
            "revenue"
        ) {

            description.textContent =
                "Top individual products by completed revenue.";

        } else {

            description.textContent =
                "Top individual products by units sold from completed orders.";

        }

    }


    function drawProductPerformance() {

        const container =
            document.getElementById(
                "product-performance-chart"
            );

        const emptyState =
            document.getElementById(
                "product-performance-empty"
            );

        if (!container) {

            return;

        }

        container.innerHTML =
            "";


        const products =
            [
                ...(
                    dashboardData.products
                    ||
                    []
                )
            ]
            .filter(
                product =>
                    (
                        product.product_name
                        &&
                        product.product_name
                            .trim()
                            .toLowerCase()
                        !==
                        "multiple products"
                    )
            )
            .sort(
                (
                    a,
                    b
                ) =>
                    Number(
                        b[
                            selectedProductMetric
                        ]
                        ||
                        0
                    )
                    -
                    Number(
                        a[
                            selectedProductMetric
                        ]
                        ||
                        0
                    )
            )
            .slice(
                0,
                8
            );


        if (
            products.length
            ===
            0
        ) {

            if (emptyState) {

                emptyState
                    .classList
                    .remove(
                        "d-none"
                    );

            }

            return;

        }


        if (emptyState) {

            emptyState
                .classList
                .add(
                    "d-none"
                );

        }


        const colors =
            chartColors();


        const width =
            Math.max(
                container.clientWidth,
                320
            );


        const compact =
            width
            <
            600;


        const rowHeight =
            compact
                ?
                72
                :
                64;


        const height =
            products.length
            *
            rowHeight;


        const rankWidth =
            45;


        const labelWidth =
            compact
                ?
                Math.min(
                    135,
                    width
                    *
                    0.38
                )
                :
                Math.min(
                    230,
                    width
                    *
                    0.31
                );


        const valueWidth =
            compact
                ?
                80
                :
                120;


        const barStart =
            rankWidth
            +
            labelWidth;


        const barWidth =
            Math.max(
                width
                -
                barStart
                -
                valueWidth
                -
                20,
                55
            );


        const maxValue =
            d3.max(
                products,
                item =>
                    Number(
                        item[
                            selectedProductMetric
                        ]
                        ||
                        0
                    )
            )
            ||
            1;


        const scale =
            d3
                .scaleLinear()
                .domain(
                    [
                        0,
                        maxValue
                    ]
                )
                .range(
                    [
                        0,
                        barWidth
                    ]
                );


        const svg =
            d3
                .select(
                    container
                )
                .append(
                    "svg"
                )
                .attr(
                    "viewBox",
                    `0 0 ${width} ${height}`
                )
                .attr(
                    "width",
                    "100%"
                )
                .attr(
                    "height",
                    height
                );


        const tooltip =
            makeTooltip(
                container
            );


        products.forEach(
            (
                product,
                index
            ) => {

                const y =
                    index
                    *
                    rowHeight;


                const value =
                    Number(
                        product[
                            selectedProductMetric
                        ]
                        ||
                        0
                    );


                const group =
                    svg
                        .append(
                            "g"
                        )
                        .attr(
                            "class",
                            "dashboard-product-row"
                        )
                        .style(
                            "cursor",
                            "default"
                        );


                if (
                    index
                    >
                    0
                ) {

                    group
                        .append(
                            "line"
                        )
                        .attr(
                            "x1",
                            0
                        )
                        .attr(
                            "x2",
                            width
                        )
                        .attr(
                            "y1",
                            y
                        )
                        .attr(
                            "y2",
                            y
                        )
                        .attr(
                            "stroke",
                            colors.border
                        )
                        .attr(
                            "stroke-opacity",
                            0.45
                        );

                }


                group
                    .append(
                        "text"
                    )
                    .attr(
                        "x",
                        4
                    )
                    .attr(
                        "y",
                        y + 39
                    )
                    .attr(
                        "fill",
                        colors.muted
                    )
                    .attr(
                        "font-size",
                        12
                    )
                    .attr(
                        "font-weight",
                        800
                    )
                    .text(
                        String(
                            index + 1
                        ).padStart(
                            2,
                            "0"
                        )
                    );


                const maxChars =
                    compact
                        ?
                        16
                        :
                        29;


                const productName =
                    String(
                        product.product_name
                        ||
                        "Unknown Product"
                    );


                const displayName =
                    productName.length
                    >
                    maxChars
                        ?
                        (
                            productName.slice(
                                0,
                                maxChars - 1
                            )
                            +
                            "…"
                        )
                        :
                        productName;


                group
                    .append(
                        "text"
                    )
                    .attr(
                        "x",
                        rankWidth
                    )
                    .attr(
                        "y",
                        y + 39
                    )
                    .attr(
                        "fill",
                        colors.text
                    )
                    .attr(
                        "font-size",
                        compact
                            ?
                            12
                            :
                            13
                    )
                    .attr(
                        "font-weight",
                        650
                    )
                    .text(
                        displayName
                    )
                    .append(
                        "title"
                    )
                    .text(
                        productName
                    );


                group
                    .append(
                        "rect"
                    )
                    .attr(
                        "x",
                        barStart
                    )
                    .attr(
                        "y",
                        y + 27
                    )
                    .attr(
                        "width",
                        barWidth
                    )
                    .attr(
                        "height",
                        11
                    )
                    .attr(
                        "rx",
                        5.5
                    )
                    .attr(
                        "fill",
                        colors.border
                    )
                    .attr(
                        "fill-opacity",
                        0.35
                    );


                group
                    .append(
                        "rect"
                    )
                    .attr(
                        "x",
                        barStart
                    )
                    .attr(
                        "y",
                        y + 27
                    )
                    .attr(
                        "height",
                        11
                    )
                    .attr(
                        "rx",
                        5.5
                    )
                    .attr(
                        "fill",
                        colors.primary
                    )
                    .attr(
                        "width",
                        0
                    )
                    .transition()
                    .duration(
                        450
                    )
                    .delay(
                        index
                        *
                        35
                    )
                    .attr(
                        "width",
                        scale(
                            value
                        )
                    );


                group
                    .append(
                        "text"
                    )
                    .attr(
                        "x",
                        width - 4
                    )
                    .attr(
                        "y",
                        y + 39
                    )
                    .attr(
                        "text-anchor",
                        "end"
                    )
                    .attr(
                        "fill",
                        colors.text
                    )
                    .attr(
                        "font-size",
                        compact
                            ?
                            11
                            :
                            13
                    )
                    .attr(
                        "font-weight",
                        750
                    )
                    .text(
                        selectedProductMetric
                        ===
                        "revenue"
                            ?
                            formatCurrency(
                                value
                            )
                            :
                            (
                                formatNumber(
                                    value
                                )
                                +
                                (
                                    value
                                    ===
                                    1
                                        ?
                                        " unit"
                                        :
                                        " units"
                                )
                            )
                    );


                group
                    .append(
                        "rect"
                    )
                    .attr(
                        "x",
                        0
                    )
                    .attr(
                        "y",
                        y
                    )
                    .attr(
                        "width",
                        width
                    )
                    .attr(
                        "height",
                        rowHeight
                    )
                    .attr(
                        "fill",
                        "transparent"
                    )
                    .on(
                        "mouseenter",
                        event => {

                            tooltip
                                .style(
                                    "display",
                                    "block"
                                )
                                .html(
                                    `
                                    <strong>
                                        ${escapeHtml(productName)}
                                    </strong>

                                    <span>
                                        Units sold:
                                        ${formatNumber(product.quantity)}
                                    </span>

                                    <span>
                                        Completed orders:
                                        ${formatNumber(product.orders)}
                                    </span>

                                    <span>
                                        Revenue:
                                        ${formatCurrency(product.revenue)}
                                    </span>
                                    `
                                );

                            moveTooltip(
                                tooltip,
                                container,
                                event
                            );

                        }
                    )
                    .on(
                        "mousemove",
                        event => {

                            moveTooltip(
                                tooltip,
                                container,
                                event
                            );

                        }
                    )
                    .on(
                        "mouseleave",
                        () => {

                            tooltip.style(
                                "display",
                                "none"
                            );

                        }
                    );

            }
        );

    }


    function resetDrilldownStates() {

        const loading =
            document.getElementById(
                "dashboard-drilldown-loading"
            );

        const error =
            document.getElementById(
                "dashboard-drilldown-error"
            );

        const empty =
            document.getElementById(
                "dashboard-drilldown-empty"
            );

        const orders =
            document.getElementById(
                "dashboard-drilldown-orders"
            );


        if (loading) {

            loading.classList.add(
                "d-none"
            );

        }


        if (error) {

            error.classList.add(
                "d-none"
            );

        }


        if (empty) {

            empty.classList.add(
                "d-none"
            );

        }


        if (orders) {

            orders.innerHTML =
                "";

        }

    }


    function platformLabel(
        platform
    ) {

        if (
            platform
            ===
            "swiggy"
        ) {

            return "Swiggy";

        }


        if (
            platform
            ===
            "insights"
        ) {

            return "Insights";

        }


        return (
            "All Platforms"
        );

    }


    function renderDrilldownOrders(
        orders
    ) {

        const container =
            document.getElementById(
                "dashboard-drilldown-orders"
            );

        if (!container) {

            return;

        }

        container.innerHTML =
            "";


        orders.forEach(
            order => {

                const platform =
                    String(
                        order.platform
                        ||
                        ""
                    ).toLowerCase();


                const item =
                    document.createElement(
                        "div"
                    );


                item.className =
                    "dashboard-drilldown-order-card";


                item.innerHTML =
                    `
                    <div class="dashboard-drilldown-order-top">

                        <div class="dashboard-drilldown-order-platform">

                            <span
                                class="platform-dot platform-${platform}"
                            >
                                ${
                                    platform
                                    ===
                                    "swiggy"
                                        ?
                                        "S"
                                        :
                                        "I"
                                }
                            </span>

                            <div>

                                <strong>
                                    ${escapeHtml(order.customer_name)}
                                </strong>

                                <span>
                                    ${escapeHtml(order.platform)}
                                </span>

                            </div>

                        </div>


                        <span
                            class="status-badge status-${escapeHtml(order.status)}"
                        >
                            ${escapeHtml(order.status)}
                        </span>

                    </div>


                    <div class="dashboard-drilldown-order-meta">

                        <span>

                            <small>
                                Order
                            </small>

                            <strong>
                                ${escapeHtml(order.order_number)}
                            </strong>

                        </span>


                        <span>

                            <small>
                                Product
                            </small>

                            <strong>
                                ${escapeHtml(order.product_name || "—")}
                            </strong>

                        </span>


                        <span>

                            <small>
                                Amount
                            </small>

                            <strong>
                                ${formatCurrency(order.amount)}
                            </strong>

                        </span>

                    </div>


                    <a
                        href="/${platform}/orders/view/${order.id}"
                        class="dashboard-drilldown-view-btn"
                    >
                        View order
                        <span>
                            →
                        </span>
                    </a>
                    `;


                container.appendChild(
                    item
                );

            }
        );

    }


    async function openDrilldown(
        platform,
        dateValue
    ) {

        const panel =
            document.getElementById(
                "dashboard-order-drilldown"
            );

        if (!panel) {

            return;

        }


        resetDrilldownStates();


        const platformElement =
            document.getElementById(
                "dashboard-drilldown-platform"
            );

        const dateElement =
            document.getElementById(
                "dashboard-drilldown-date"
            );

        const metricElement =
            document.getElementById(
                "dashboard-drilldown-metric"
            );

        const badgeElement =
            document.getElementById(
                "dashboard-drilldown-badge"
            );

        const countElement =
            document.getElementById(
                "dashboard-drilldown-count"
            );

        const amountElement =
            document.getElementById(
                "dashboard-drilldown-total"
            );

        const loading =
            document.getElementById(
                "dashboard-drilldown-loading"
            );

        const error =
            document.getElementById(
                "dashboard-drilldown-error"
            );

        const empty =
            document.getElementById(
                "dashboard-drilldown-empty"
            );


        if (platformElement) {

            platformElement.textContent =
                platformLabel(
                    platform
                );

        }


        if (dateElement) {

            dateElement.textContent =
                formatFullDate(
                    dateValue
                );

        }


        if (metricElement) {

            metricElement.textContent =
                metricConfig[
                    selectedMetric
                ].label;

        }


        if (badgeElement) {

            badgeElement.textContent =
                metricConfig[
                    selectedMetric
                ].label;

        }


        if (countElement) {

            countElement.textContent =
                "0";

        }


        if (amountElement) {

            amountElement.textContent =
                "₹0.00";

        }


        const offcanvas =
            bootstrap
                .Offcanvas
                .getOrCreateInstance(
                    panel
                );


        offcanvas.show();


        if (loading) {

            loading.classList.remove(
                "d-none"
            );

        }


        try {

            const params =
                new URLSearchParams(
                    {
                        platform:
                            platform,

                        metric:
                            selectedMetric,

                        date:
                            dateValue
                    }
                );


            const response =
                await fetch(
                    `/api/dashboard/orders?${params.toString()}`
                );


            if (
                !response.ok
            ) {

                throw new Error(
                    "Unable to retrieve dashboard orders."
                );

            }


            const data =
                await response.json();


            if (loading) {

                loading.classList.add(
                    "d-none"
                );

            }


            if (countElement) {

                countElement.textContent =
                    formatNumber(
                        data.order_count
                    );

            }


            if (amountElement) {

                amountElement.textContent =
                    formatCurrency(
                        data.total_amount
                    );

            }


            if (
                metricElement
                &&
                data.metric_label
            ) {

                metricElement.textContent =
                    data.metric_label;

            }


            const orders =
                data.orders
                ||
                [];


            if (
                orders.length
                ===
                0
            ) {

                if (empty) {

                    empty.classList.remove(
                        "d-none"
                    );

                }

                return;

            }


            renderDrilldownOrders(
                orders
            );

        }

        catch (
            requestError
        ) {

            console.error(
                "Dashboard drilldown error:",
                requestError
            );


            if (loading) {

                loading.classList.add(
                    "d-none"
                );

            }


            if (error) {

                error.classList.remove(
                    "d-none"
                );

            }

        }

    }


    function drawAll() {

        if (!dashboardData) {

            return;

        }


        const colors =
            chartColors();


        updateAnalysisSummaries();


        drawPlatformTrend(
            "swiggy-dashboard-chart",
            dashboardData
                .swiggy
                .trend
            ||
            [],
            colors.swiggy,
            "swiggy"
        );


        drawCombinedComparison();


        drawPlatformTrend(
            "insights-dashboard-chart",
            dashboardData
                .insights
                .trend
            ||
            [],
            colors.insights,
            "insights"
        );


        drawProductPerformance();

    }


    function bindControls() {

        document
            .querySelectorAll(
                ".dashboard-metric-btn"
            )
            .forEach(
                button => {

                    button.addEventListener(
                        "click",
                        () => {

                            selectedMetric =
                                button
                                    .dataset
                                    .metric;


                            document
                                .querySelectorAll(
                                    ".dashboard-metric-btn"
                                )
                                .forEach(
                                    item => {

                                        item
                                            .classList
                                            .remove(
                                                "active"
                                            );

                                    }
                                );


                            button
                                .classList
                                .add(
                                    "active"
                                );


                            drawAll();

                        }
                    );

                }
            );


        document
            .querySelectorAll(
                ".dashboard-product-btn"
            )
            .forEach(
                button => {

                    button.addEventListener(
                        "click",
                        () => {

                            selectedProductMetric =
                                button
                                    .dataset
                                    .productMetric;


                            document
                                .querySelectorAll(
                                    ".dashboard-product-btn"
                                )
                                .forEach(
                                    item => {

                                        item
                                            .classList
                                            .remove(
                                                "active"
                                            );

                                    }
                                );


                            button
                                .classList
                                .add(
                                    "active"
                                );


                            updateProductDescription();

                            drawProductPerformance();

                        }
                    );

                }
            );

    }


    document.addEventListener(
        "DOMContentLoaded",
        () => {

            const dataElement =
                document.getElementById(
                    "dashboard-data"
                );


            if (!dataElement) {

                return;

            }


            if (
                typeof d3
                ===
                "undefined"
            ) {

                console.error(
                    "D3.js is not loaded."
                );

                return;

            }


            try {

                dashboardData =
                    JSON.parse(
                        dataElement.textContent
                    );

            }

            catch (
                error
            ) {

                console.error(
                    "Unable to read dashboard data:",
                    error
                );

                return;

            }


            normalizeProductControls();

            bindControls();

            updateProductDescription();

            drawAll();


            window.addEventListener(
                "resize",
                () => {

                    clearTimeout(
                        resizeTimer
                    );


                    resizeTimer =
                        setTimeout(
                            drawAll,
                            150
                        );

                }
            );


            window.addEventListener(
                "themechange",
                () => {

                    setTimeout(
                        drawAll,
                        30
                    );

                }
            );

        }
    );

})();