import React, { useState, useRef, useEffect } from 'react';
import {
    Modal,
    ModalOverlay,
    ModalContent,
    ModalHeader,
    ModalFooter,
    ModalBody,
    ModalCloseButton,
    Button,
    Box,
    Flex,
    Text,
    NumberInput,
    NumberInputField,
    NumberInputStepper,
    NumberIncrementStepper,
    NumberDecrementStepper,
    useColorModeValue,
} from '@chakra-ui/react';
import type { RangeWeight } from '../../../types';

export type { RangeWeight } from '../../../types';

interface Props {
    isOpen: boolean;
    onClose: () => void;
    onSave: (weights: RangeWeight[]) => void;
    initialWeights?: RangeWeight[];
}

const labels = ["Starting", "Evaporation", "Other", "Oxidation"];

const AbnormalityWeightDialog: React.FC<Props> = ({
    isOpen,
    onClose,
    onSave,
    initialWeights
}) => {
    const [breakpoints, setBreakpoints] = useState<number[]>([2750, 2000, 1750, 550]);
    const [weights, setWeights] = useState<number[]>([10, 20, 10, 60]);
    // Separate controlled string state so manual typing (including empty/partial) works smoothly
    const [weightInputs, setWeightInputs] = useState<string[]>(["10", "20", "10", "60"]);
    const [draggingIndex, setDraggingIndex] = useState<number | null>(null);
    const trackRef = useRef<HTMLDivElement>(null);

    // Color mode values
    const trackBg = useColorModeValue('gray.200', 'gray.700');
    const regionBg = useColorModeValue('white', 'gray.800');
    const textColor = useColorModeValue('gray.800', 'gray.100');
    
    // Handle colors adapt to dark mode
    const handleColors = [
        useColorModeValue("black", "gray.100"),
        useColorModeValue("gray.700", "gray.400"),
        useColorModeValue("gray.500", "gray.500"),
        useColorModeValue("gray.300", "gray.600")
    ];

    const MIN = 550;
    const MAX = 4000;

    const totalWeight = weights.reduce((sum, w) => sum + w, 0);
    const inputsAllValid = weightInputs.every((v) => {
        if (v === '') return false;
        const n = parseInt(v, 10);
        return !isNaN(n) && n >= 1 && n <= 97;
    });
    const isValid = totalWeight === 100 && inputsAllValid;

    useEffect(() => {
        if (draggingIndex === null) return;

        const handleMouseMove = (e: MouseEvent) => {
            if (!trackRef.current) return;

            const rect = trackRef.current.getBoundingClientRect();
            const percentage = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
            const reversedPercentage = 1 - percentage;
            const newValue = MIN + reversedPercentage * (MAX - MIN);

            setBreakpoints((prev) => {
                const updated = [...prev];
                updated[draggingIndex] = Math.max(MIN, Math.min(MAX, newValue));
                updated.sort((a, b) => b - a);
                return updated;
            });
        };

        const handleMouseUp = () => {
            setDraggingIndex(null);
        };

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);

        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };
    }, [draggingIndex]);

    // Handle immediate typing; allow empty/partial strings, update numeric state when valid
    const updateWeightInput = (index: number, valueString: string) => {
        // Accept only digits and empty string
        if (!/^\d*$/.test(valueString)) return;

        setWeightInputs((prev) => {
            const next = [...prev];
            next[index] = valueString;
            return next;
        });

        // Defer clamping until commit; only update live numeric weights when in valid range
        if (valueString !== '') {
            const numValue = parseInt(valueString, 10);
            if (!isNaN(numValue) && numValue >= 1 && numValue <= 97) {
                setWeights((prev) => {
                    const next = [...prev];
                    next[index] = numValue;
                    return next;
                });
            }
        }
    };

    // Commit value on blur/enter: coerce to 1..97 and sync both states
    const commitWeightInput = (index: number) => {
        const current = weightInputs[index];
        const numValue = parseInt(current, 10);
        const clamped = isNaN(numValue) ? 1 : Math.max(1, Math.min(97, numValue));
        setWeights((prev) => {
            const next = [...prev];
            next[index] = clamped;
            return next;
        });
        setWeightInputs((prev) => {
            const next = [...prev];
            next[index] = String(clamped);
            return next;
        });
    };

    const handleMouseDown = (index: number) => {
        setDraggingIndex(index);
    };

    const getPosition = (value: number) => (1 - (value - MIN) / (MAX - MIN)) * 100;

    const handleSave = () => {
        if (!isValid) return;

        // Convert to RangeWeight format (weights are already 0-100, just pass them directly)
        const rangeWeights: RangeWeight[] = [];

        rangeWeights.push({
            min: breakpoints[0],
            max: MAX,
            weight: weights[0],
            label: `${labels[0]} (${MAX}-${Math.round(breakpoints[0])} cm⁻¹)`,
            key: 'range_starting'
        });

        rangeWeights.push({
            min: breakpoints[1],
            max: breakpoints[0],
            weight: weights[1],
            label: `${labels[1]} (${Math.round(breakpoints[0])}-${Math.round(breakpoints[1])} cm⁻¹)`,
            key: 'range_evaporation'
        });

        rangeWeights.push({
            min: breakpoints[2],
            max: breakpoints[1],
            weight: weights[2],
            label: `${labels[2]} (${Math.round(breakpoints[1])}-${Math.round(breakpoints[2])} cm⁻¹)`,
            key: 'range_other'
        });

        rangeWeights.push({
            min: MIN,
            max: breakpoints[2],
            weight: weights[3],
            label: `${labels[3]} (${Math.round(breakpoints[2])}-${MIN} cm⁻¹)`,
            key: 'range_oxidation'
        });

        onSave(rangeWeights);
        onClose();
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose} size="3xl" scrollBehavior="inside">
            <ModalOverlay />
            <ModalContent maxW="800px">
                <ModalHeader fontSize="2xl" fontWeight="bold">Interval Weight Selector</ModalHeader>
                <ModalCloseButton />

                <ModalBody>
                    <Box mb={6}>
                        {/* Range slider track */}
                        <Box
                            ref={trackRef}
                            position="relative"
                            h="8px"
                            bg={trackBg}
                            borderRadius="full"
                            cursor="pointer"
                            userSelect="none"
                        >
                            {breakpoints.map((value, index) => {
                                const position = getPosition(value);
                                return (
                                    <Box
                                        key={index}
                                        position="absolute"
                                        top="50%"
                                        transform="translateY(-50%)"
                                        w="20px"
                                        h="20px"
                                        borderRadius="full"
                                        border="2px solid white"
                                        bg={handleColors[index]}
                                        boxShadow="md"
                                        cursor="grab"
                                        _active={{ cursor: 'grabbing' }}
                                        _hover={{ transform: 'translateY(-50%) scale(1.1)' }}
                                        transition="all 0.075s"
                                        left={`calc(${position}% - 10px)`}
                                        zIndex={draggingIndex === index ? 50 : 10}
                                        onMouseDown={() => handleMouseDown(index)}
                                    />
                                );
                            })}
                        </Box>

                        {/* Range labels */}
                        <Flex justify="space-between" mt={2} fontSize="xs" color={useColorModeValue('gray.500', 'gray.400')}>
                            <Text>{MAX}</Text>
                            <Text>{MIN}</Text>
                        </Flex>
                    </Box>

                    <Box>
                        {labels.map((label, index) => {
                            const rangeStart = index === 0 ? MAX : Math.round(breakpoints[index - 1]);
                            const rangeEnd = Math.round(breakpoints[index]);
                            const inputStr = weightInputs[index];
                            const fieldBorderColor = (() => {
                                if (inputStr === '') return 'orange.300';
                                const n = parseInt(inputStr, 10);
                                if (isNaN(n) || n < 1 || n > 97) return 'red.400';
                                return useColorModeValue('gray.200', 'gray.600');
                            })();

                            return (
                                <Box
                                    key={index}
                                    mb={3}
                                    p={4}
                                    bg={regionBg}
                                    border="1px"
                                    borderColor={useColorModeValue('gray.200', 'gray.600')}
                                    borderRadius="lg"
                                >
                                    <Flex align="center" justify="space-between" gap={4}>
                                        <Box flex={1}>
                                            <Flex align="center" gap={2} mb={2}>
                                                <Box w="12px" h="12px" borderRadius="full" bg={handleColors[index]} />
                                                <Text fontWeight="semibold" color={textColor}>{label}</Text>
                                            </Flex>
                                            <Text fontSize="xs" color={useColorModeValue('gray.500', 'gray.400')}>
                                                Range: {rangeStart} → {rangeEnd} cm⁻¹
                                            </Text>
                                        </Box>
                                        <Box>
                                            <Text fontSize="xs" fontWeight="medium" color={useColorModeValue('gray.500', 'gray.400')} mb={1}>
                                                Weight
                                            </Text>
                                            <NumberInput
                                                step={1}
                                                value={weightInputs[index]}
                                                onChange={(valueString) => updateWeightInput(index, valueString)}
                                                size="sm"
                                                w="80px"
                                                allowMouseWheel
                                            >
                                                <NumberInputField
                                                    textAlign="center"
                                                    onBlur={() => commitWeightInput(index)}
                                                    onKeyDown={(e) => {
                                                        if (e.key === 'Enter') {
                                                            commitWeightInput(index);
                                                        }
                                                    }}
                                                    borderColor={fieldBorderColor}
                                                />
                                                <NumberInputStepper>
                                                    <NumberIncrementStepper onClick={() => {
                                                        commitWeightInput(index); // ensure current value committed
                                                        setWeights((prev) => {
                                                            const next = [...prev];
                                                            const inc = Math.min(97, next[index] + 1);
                                                            next[index] = inc;
                                                            return next;
                                                        });
                                                        setWeightInputs((prev) => {
                                                            const next = [...prev];
                                                            next[index] = String(Math.min(97, parseInt(next[index] || '0', 10) + 1 || 1));
                                                            return next;
                                                        });
                                                    }} />
                                                    <NumberDecrementStepper onClick={() => {
                                                        commitWeightInput(index);
                                                        setWeights((prev) => {
                                                            const next = [...prev];
                                                            const dec = Math.max(1, next[index] - 1);
                                                            next[index] = dec;
                                                            return next;
                                                        });
                                                        setWeightInputs((prev) => {
                                                            const next = [...prev];
                                                            const current = parseInt(next[index] || '0', 10) || 1;
                                                            next[index] = String(Math.max(1, current - 1));
                                                            return next;
                                                        });
                                                    }} />
                                                </NumberInputStepper>
                                            </NumberInput>
                                        </Box>
                                    </Flex>
                                </Box>
                            );
                        })}
                    </Box>

                    <Box
                        p={4}
                        borderRadius="lg"
                        border="1px"
                        borderColor={isValid ? useColorModeValue('gray.200', 'gray.600') : 'red.400'}
                        bg={regionBg}
                    >
                        <Flex justify="space-between" align="center">
                            <Text fontSize="sm" fontWeight="medium" color={useColorModeValue('gray.600', 'gray.400')}>
                                Total Weight:
                            </Text>
                            <Text fontSize="lg" fontWeight="bold" color={isValid ? textColor : 'red.500'}>
                                {totalWeight} / 100
                                {!isValid && ' ⚠'}
                            </Text>
                        </Flex>
                    </Box>
                </ModalBody>

                <ModalFooter>
                    <Button variant="ghost" mr={3} onClick={onClose}>
                        Cancel
                    </Button>
                    <Button
                        colorScheme="blue"
                        onClick={handleSave}
                        isDisabled={!isValid}
                    >
                        Save Weights
                    </Button>
                </ModalFooter>
            </ModalContent>
        </Modal>
    );
};

export default AbnormalityWeightDialog;
