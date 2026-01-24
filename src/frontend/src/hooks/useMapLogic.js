import { useState } from 'react';

export function useMapLogic() {
    const [markers, setMarkers] = useState([]);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [currentDrop, setCurrentDrop] = useState(null);
    const [metaInput, setMetaInput] = useState({ desc: "", altura: "" });

    // Drag & Drop Handlers (UI Logic)
    const handleDragStart = (e, type) => {
        e.dataTransfer.setData("symbolType", type);
        e.dataTransfer.effectAllowed = "copy";
    };

    const handleSymbolDrop = (latlng, type) => {
        setCurrentDrop({ latlng, type });
        setMetaInput({ desc: "", altura: "" });
        setIsModalOpen(true);
    };

    const confirmMarker = () => {
        if (!currentDrop) return;
        setMarkers(prev => [...prev, {
            lat: currentDrop.latlng.lat,
            lon: currentDrop.latlng.lng,
            tipo: currentDrop.type,
            meta: { ...metaInput }
        }]);
        setIsModalOpen(false);
        setCurrentDrop(null);
    };

    const cancelMarker = () => {
        setIsModalOpen(false);
        setCurrentDrop(null);
    };

    return {
        markers,
        setMarkers, // <--- EXPOSTO AQUI
        isModalOpen,
        currentDrop,
        metaInput,
        setMetaInput,
        handleDragStart,
        handleSymbolDrop,
        confirmMarker,
        cancelMarker
    };
}