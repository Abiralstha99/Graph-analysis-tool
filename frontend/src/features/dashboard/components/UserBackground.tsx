import React from 'react';
import { Box, BoxProps } from '@chakra-ui/react';

interface UserBackgroundProps extends BoxProps {
    backgroundUrl?: string;
    defaultGradient?: string;
}

/**
 * UserBackground Component
 * 
 * Displays a customizable background for user profile or dashboard sections.
 * If no backgroundUrl is provided, it falls back to a gradient background.
 */
const UserBackground: React.FC<UserBackgroundProps> = ({
    backgroundUrl,
    defaultGradient = 'linear(to-r, blue.400, purple.500)',
    children,
    ...props
}) => {
    return (
        <Box
            width="100%"
            height="200px"
            position="relative"
            borderRadius="lg"
            overflow="hidden"
            backgroundImage={
                backgroundUrl
                    ? `url(${backgroundUrl})`
                    : undefined
            }
            bgGradient={!backgroundUrl ? defaultGradient : undefined}
            backgroundSize="cover"
            backgroundPosition="center"
            backgroundRepeat="no-repeat"
            {...props}
        >
            {children}
        </Box>
    );
};

export default UserBackground;
