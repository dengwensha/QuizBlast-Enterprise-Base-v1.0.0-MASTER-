import QBCard from "./QBCard";

export default function QBStatCard({
    title,
    value,
    icon
}) {

    return (

        <QBCard>

            <div>{icon}</div>

            <div>{title}</div>

            <h2>{value}</h2>

        </QBCard>

    );

}